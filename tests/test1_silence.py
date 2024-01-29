from pydub import AudioSegment
from pydub.silence import split_on_silence

def remove_silence(input_file, output_file, silence_threshold=-40):
    # Load the audio file
    audio = AudioSegment.from_file(input_file)

    # Split the audio based on silence
    segments = split_on_silence(audio, silence_thresh=silence_threshold)

    # Concatenate non-silent segments
    output_audio = AudioSegment.silent()
    for segment in segments:
        output_audio += segment

    # Export the result to a new file
    output_audio.export(output_file, format="wav")

if __name__ == "__main__":
    # Replace 'input_audio.wav' and 'output_audio.wav' with your input and output file paths
    input_file = r'Data\recording_06012024233332.m4a'
    output_file = r'Data\output_audio.wav'

    # Adjust the silence threshold if needed (default is -40 dB)
    silence_threshold = -50

    remove_silence(input_file, output_file, silence_threshold)
    print(f"Silent sections removed. Result saved to {output_file}")
