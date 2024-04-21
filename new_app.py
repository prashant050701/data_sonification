import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from io import BytesIO
from astroquery.skyview import SkyView
from astropy import coordinates as coords
from astropy import units as u
from new_sonification_utils import sonify_image, pyfluidsynth_sonify, calculate_column_averages, map_to_midi
import time
import fluidsynth

# Define the available instruments and their corresponding program numbers
instruments = {
    "Acoustic Grand Piano": 0,
    "Bright Acoustic Piano": 1,
    "Electric Guitar (clean)": 27,
    "String Ensemble 1": 48,
    "Church Organ": 19,
    "Violin": 40,
    "Trumpet": 56,
}

@st.cache_data
def get_skyview_image(ra, dec, unit, survey, width, height):
    try:
        co = coords.SkyCoord(ra, dec, unit=unit, frame='icrs')
        img_data = SkyView.get_images(position=co, survey=survey, pixels=(width, height), radius=0.2 * u.deg)
        return img_data[0][0].data
    except Exception as e:
        st.error(f"Failed to fetch image for {survey}: {str(e)}")
        return None

def create_wave_animation(rgb_image, column_index, width, height):
    fig, ax = plt.subplots()
    ax.imshow(rgb_image)
    ax.axvline(x=column_index, color='red', alpha=0.5)
    ax.set_xlim(0, width)
    ax.set_ylim(height, 0)
    ax.set_xticks([])
    ax.set_yticks([])
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=80)
    buf.seek(0)
    frame = Image.open(buf)
    plt.close(fig)
    return frame

st.title('Data Sonification of Astronomical Images')

# UI for coordinate input
coord_format = st.selectbox('Choose coordinate format:', ('HMS/DMS', 'Degrees'))
if coord_format == 'HMS/DMS':
    ra = st.text_input('RA (hh:mm:ss.ss):', value='13:29:56.27')
    dec = st.text_input('Dec (dd:mm:ss.ss):', value='+47:13:50.02')
    unit = ('hourangle', 'deg')
else:
    ra = st.text_input('RA (decimal degrees):', value='202.484458')
    dec = st.text_input('Dec (decimal degrees):', value='47.230561')
    unit = 'deg'
bands = ['SDSSu', 'SDSSg', 'SDSSr', 'SDSSi', 'SDSSz']
size = st.slider('Select image size (width and height in pixels):', min_value=64, max_value=512, value=256, step=64)
width = height = size
images = [get_skyview_image(ra, dec, unit=unit, survey=band, width=width, height=height) for band in bands]
available_images = [img for img in images if img is not None]

if not available_images:
    st.write('Image not available for the given location.')
else:
    rgb_image = np.stack(available_images[:3], axis=-1)
    rgb_image = np.clip(rgb_image, 0, 1)
    st.image(rgb_image, caption='Image of the location', use_column_width=True)

sonification_type = st.selectbox('Choose Sonification Type:', ['Original', 'FluidSynth'])

if sonification_type == 'FluidSynth':
    instrument_name = st.selectbox('Select Instrument:', list(instruments.keys()))

if st.button('Sonify'):
    if sonification_type == 'FluidSynth':
        column_averages = calculate_column_averages(available_images)
        column_midi = map_to_midi(column_averages)
        fs = fluidsynth.Synth()
        fs.start(driver="alsa")  # Changed from coreaudio to alsa for Linux compatibility
        sfid = fs.sfload('GeneralUser GS 1.471/GeneralUser GS v1.471.sf2')
        fs.program_select(0, sfid, 0, instruments[instrument_name])

        wave_placeholder = st.empty()
        for i, note_number in enumerate(column_midi):
            fs.noteon(0, note_number, 50)
            wave_image = create_wave_animation(rgb_image, i, width, height)
            wave_placeholder.image(wave_image, use_column_width=True, caption=f'Column {i}')
            fs.noteoff(0, note_number)

        fs.delete()
    else:
        # Original sonification logic
        audio_segments_with_indices = sonify_image(available_images)
        wave_placeholder = st.empty()
        for audio_segment, column_index in audio_segments_with_indices:
            wave_image = create_wave_animation(rgb_image, column_index, width, height)
            wave_placeholder.image(wave_image, use_column_width=True, caption=f'Column {column_index}')
            # Removed playback via sounddevice for compatibility with cloud hosting
