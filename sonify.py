import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from io import BytesIO
from astroquery.skyview import SkyView
from astropy import coordinates as coords
from astropy import units as u
from pydub import AudioSegment, generators
import sounddevice as sd


@st.cache_data
def get_skyview_image(ra, dec, unit, survey, width, height):
    try:
        co = coords.SkyCoord(ra, dec, unit=unit, frame='icrs')
        img_data = SkyView.get_images(position=co, survey=survey, pixels=(width, height), radius=0.2 * u.deg)
        return img_data[0][0].data.reshape(height, width)
    except:
        return None

def sonify_image(images, base_frequency=200, sweep_speed=50, duration=50, overlap=.5):
    width = images[0].shape[1]

    for x in range(width):
        column_avg = 0
        for img in images:
            if img is None:
                continue
            column_avg += img[:, x].mean()
        column_avg /= len(images)
        freq = base_frequency + column_avg * sweep_speed
        sine_wave = generators.Sine(freq).to_audio_segment(duration=duration)
        fade_duration = int(duration * overlap)
        sine_wave = sine_wave.fade_in(fade_duration).fade_out(fade_duration)
        yield sine_wave, x

def create_wave_animation(rgb_image, column_index, width, height):
    fig, ax = plt.subplots()
    ax.imshow(rgb_image)

    # Overlay the sound wave data on the image
    x_position = column_index
    ax.axvline(x_position, color='r', alpha=0.5)
    ax.set_xlim(0, width)
    ax.set_ylim(height, 0)
    ax.set_xticks([])
    ax.set_yticks([])

    # Save the plot as an image
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=80)
    buf.seek(0)
    frame = Image.open(buf)

    plt.close(fig)

    return frame


st.title('Data Sonification')

coord_format = st.selectbox('Choose coordinate format:', ('HMS/DMS', 'Degrees'))
if coord_format == 'HMS/DMS':
    ra = st.text_input('RA (hh:mm:ss.ss):', value='13:29:56.27')
    dec = st.text_input('Dec (dd:mm:ss.ss):', value='+47:13:50.02')
    unit = ('hourangle', 'deg')
else:
    ra = st.text_input('RA (decimal degrees):', value='202.484458')
    dec = st.text_input('Dec (decimal degrees):', value='47.230561')
    unit = 'deg'

# Add a slider for width and height
size = st.slider('Select image size (width and height in pixels):', min_value=64, max_value=512, value=256, step=64)
width = size
height = size

# Display a message about larger images
st.write('Note: Larger images may take longer to load.')

bands = ['SDSSu', 'SDSSg', 'SDSSr', 'SDSSI', 'SDSSz']
images = [get_skyview_image(ra, dec, unit=unit, survey=band, width=width, height=height) for band in bands]

if all([img is None for img in images]):
    st.write('Image not available for the given location.')
else:
    available_images = [img for img in images if img is not None]
    rgb_image = np.stack((available_images[1], available_images[2], available_images[3]), axis=-1)
    rgb_image = np.log1p(rgb_image - np.min(rgb_image)) / np.log1p(np.max(rgb_image) - np.min(rgb_image))
    rgb_image = (rgb_image * 255).astype(np.uint8)

    st.image(rgb_image, caption='Image of the location', use_column_width=True)

if st.button('Sonify'):
    audio = AudioSegment.silent(duration=0)
    wave_placeholder = st.empty()

    for sine_wave, column_index in sonify_image(images):
        audio += sine_wave

        wave_image = create_wave_animation(rgb_image, column_index, width, height)
        wave_placeholder.image(wave_image, use_column_width=True, caption='Wave sweeping across the image')

        sd.play(sine_wave.get_array_of_samples(), samplerate=sine_wave.frame_rate)
