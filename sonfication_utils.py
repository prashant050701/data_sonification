from pydub import AudioSegment
from pydub.generators import Sine

def note_to_freq(note):
    """ Convert a MIDI note number to a frequency in Hz. """
    return 440 * (2 ** ((note - 69) / 12))

def sonify_image_by_filter(images, filters, duration=50, overlap=0.5):
    width = images[0].shape[1]
    note_ranges = {
        'SDSSu': (21, 32),
        'SDSSg': (33, 44),
        'SDSSr': (45, 56),
        'SDSSI': (57, 68),
        'SDSSz': (69, 80)
    }
    
    audio_columns = []

    for x in range(width):
        combined_audio = AudioSegment.silent(duration=duration)
        for img, filter_name in zip(images, filters):
            if img is None:
                continue
            column_mean = img[:, x].mean()
            min_val, max_val = img.min(), img.max()
            
            # Normalize and map to the corresponding note range
            normalized_intensity = (column_mean - min_val) / (max_val - min_val) if max_val > min_val else 0
            note_range = note_ranges.get(filter_name, (21, 32))
            midi_note = int(normalized_intensity * (note_range[1] - note_range[0]) + note_range[0])
            freq = note_to_freq(midi_note)
            
            # Generate sine wave for the note
            sine_wave = Sine(freq)
            audio_segment = sine_wave.to_audio_segment(duration=duration)
            
            fade_duration = int(duration * overlap)
            audio_segment = audio_segment.fade_in(fade_duration).fade_out(fade_duration)
            
            # Combine audio from different filters
            combined_audio = combined_audio.overlay(audio_segment)
        
        audio_columns.append((combined_audio, x))
    
    return audio_columns
