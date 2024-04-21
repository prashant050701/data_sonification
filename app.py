import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from io import BytesIO
from astroquery.skyview import SkyView
from astropy import coordinates as coords
from astropy import units as u
import sounddevice as sd
from pydub import AudioSegment
from sonification_utils import sonify_image_by_filter

@st.cache_data
def get_skyview_image(ra, dec, unit, survey, width, height):
    try:
        co = coords.SkyCoord(ra, dec, unit=unit, frame='icrs')
        img_data = SkyView.get_images(position=co, survey=survey, pixels=(width, height), radius=0.2 * u.deg)
        return img_data[0][0].data
    except Exception as e:
        st.error(f"Failed to fetch image for {survey}: {str(e)}")
        return None

def process_image_for_rgb(images, bands):
    band_indices = {band: idx for idx, band in enumerate(bands)}
    required_bands = ['SDSSg', 'SDSSr', 'SDSSz']  # Adjust bands for RGB as needed

    try:
        rgb_images = [images[band_indices[band]] for band in required_bands]
        processed_images = []
        for img in rgb_images:
            if img is None:
                raise ValueError("Missing required band data for RGB image.")
            processed_img = np.log1p(img - np.min(img)) / np.log1p(np.max(img) - np.min(img))
            processed_images.append(processed_img * 255)
        rgb_image = np.stack(processed_images, axis=-1).astype(np.uint8)
        return rgb_image
    except KeyError:
        st.error("One or more required bands are not present in the input.")
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

coord_format = st.selectbox('Choose coordinate format:', ('HMS/DMS', 'Degrees'))
if coord_format == 'HMS/DMS':
    ra = st.text_input('RA (hh:mm:ss.ss):', value='13:29:56.27')
    dec = st.text_input('Dec (dd:mm:ss.ss):', value='+47:13:50.02')
    unit = ('hourangle', 'deg')
else:
    ra = st.text_input('RA (decimal degrees):', value='202.484458')
    dec = st.text_input('Dec (decimal degrees):', value='47.230561')
    unit = 'deg'

size = st.slider('Select image size (width and height in pixels):', min_value=64, max_value=512, value=256, step=64)
width = height = size
bands = ['SDSSu', 'SDSSg', 'SDSSr', 'SDSSi', 'SDSSz']
images = [get_skyview_image(ra, dec, unit=unit, survey=band, width=width, height=height) for band in bands]
available_images = [img for img in images if img is not None]

if all(img is None for img in images):
    st.write('No images available for the given location.')
else:
    rgb_image = np.stack(available_images[:3], axis=-1)  # Only first three for RGB channels
    rgb_image = np.clip(rgb_image, 0, 1)  # Normalize if needed
    st.image(rgb_image, caption='Image of the location', use_column_width=True)

# Triggered by the 'Sonify' button in the Streamlit interface
if st.button('Sonify'):
    audio = AudioSegment.silent(duration=0)
    wave_placeholder = st.empty()

    for combined_audio, column_index in sonify_image_by_filter(images, bands, duration=50, overlap=0.5):
        audio += combined_audio
        wave_image = create_wave_animation(rgb_image, column_index, width, height)
        wave_placeholder.image(wave_image, use_column_width=True, caption='Wave sweeping across the image')
        sd.play(combined_audio.get_array_of_samples(), samplerate=combined_audio.frame_rate)
