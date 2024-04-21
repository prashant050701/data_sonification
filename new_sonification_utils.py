import numpy as np
import pretty_midi
from pydub import AudioSegment, generators
import fluidsynth
import time
def frequency_from_midi(midi_note):
    """Converts a MIDI note number to a frequency in Hz."""
    return 440.0 * (2 ** ((midi_note - 69) / 12.0))

def calculate_column_averages(images):
    """Calculate the average intensity for each column across the list of images."""
    height, width = images[0].shape
    column_averages = np.zeros(width)
    for img in images:
        column_averages += np.mean(img, axis=0)
    column_averages /= len(images)
    return column_averages

def map_to_midi(column_averages, midi_min=21, midi_max=108):
    """Map the average values to MIDI note numbers."""
    max_val = np.max(column_averages)
    min_val = np.min(column_averages)
    return np.round(midi_min + (midi_max - midi_min) * (column_averages - min_val) / (max_val - min_val)).astype(int)


def pyfluidsynth_sonify(images, soundfont_path, instrument_index=0, scale_type='major', duration=0.5, velocity=50):
    """Create sonification using pyfluidsynth with the specified SoundFont."""
    if not images:
        return None  # Nothing to sonify

    fs = fluidsynth.Synth()
    fs.start(driver="coreaudio")  # Use "coreaudio" for macOS, "dsound" for Windows, or "alsa" for Linux

    sfid = fs.sfload(soundfont_path)
    fs.program_select(0, sfid, 0, instrument_index)  # Select the instrument

    column_averages = calculate_column_averages(images)
    column_midi = map_to_midi(column_averages)

    # Play notes
    for note_number in column_midi:
        fs.noteon(0, note_number, velocity)
        time.sleep(duration)  # Correctly using time.sleep instead of fs.sleep
        fs.noteoff(0, note_number)

    fs.delete()
    return None

def generate_sound(midi_note, duration=50, overlap=0.5):
    """Convert MIDI notes to frequencies and generate the corresponding sound."""
    freq = frequency_from_midi(midi_note)
    sine_wave = generators.Sine(freq).to_audio_segment(duration=duration)
    fade_duration = int(duration * overlap)
    return sine_wave.fade_in(fade_duration).fade_out(fade_duration)

def pretty_midi_sonify(images, instrument_name='Acoustic Grand Piano', scale_type='major', duration=0.5, velocity=100):
    """Create sonification using PrettyMidi with options for different instruments and musical scales."""
    if not images:
        return pretty_midi.PrettyMIDI()  # Return an empty PrettyMIDI object

    column_averages = calculate_column_averages(images)
    column_midi = map_to_midi(column_averages)

    midi = pretty_midi.PrettyMIDI()
    instrument = pretty_midi.Instrument(program=pretty_midi.instrument_name_to_program(instrument_name))

    start_time = 0.0
    for note_number in column_midi:
        note = pretty_midi.Note(
            velocity=velocity, pitch=note_number, start=start_time, end=start_time + duration
        )
        instrument.notes.append(note)
        start_time += duration + 0.05  # Add a small gap between notes

    midi.instruments.append(instrument)
    return midi  # Return the PrettyMIDI object


def sonify_image(images, scale_type='major', duration=50, overlap=0.5):
    """Generate audio segments for each column in images, based on their average intensities."""
    if not images:
        return [(AudioSegment.silent(duration=1000), 0)]

    column_averages = calculate_column_averages(images)
    column_midi = map_to_midi(column_averages)
    audio_segments = [generate_sound(midi_note, duration, overlap) for midi_note in column_midi]

    return list(zip(audio_segments, range(len(column_midi))))
