from spleeter.separator import Separator
from urllib.parse import unquote_plus
import json
import os
import subprocess
from pydub import AudioSegment
from pydub.silence import split_on_silence

silence_threshold = -45

audio_codec = "mp3"
output_destination = r".\Data\audio_output"
filename_format = "{instrument}.{codec}"

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
    output_audio.export(output_file, format=audio_codec)

def normalize_audio(input_file, output_file):
    # Load the audio file using pydub
    audio = AudioSegment.from_file(input_file)

    # Normalize the loudness to -20 dBFS
    normalized_audio = audio.normalize()

    # Export the normalized audio to the output file
    normalized_audio.export(output_file, format=audio_codec)

if __name__ == "__main__":
    print("Execution starting!")

    # Input
    input_lambda_file_path = r'Data\recording_06012024233332.m4a'

    separator = Separator("spleeter:2stems", multiprocess=False)
    print(f"input_lambda_file_path: {input_lambda_file_path}\noutput_destination: {output_destination}\nfilename_format: {filename_format}\naudio_codec: {audio_codec}")
    separator.separate_to_file(input_lambda_file_path, output_destination, filename_format=filename_format, codec=audio_codec, synchronous=True)

    # Separated files, identifying vocals file path
    vocals_filename = f"vocals.{audio_codec}"
    vocals_path = f"{output_destination_file_path}/{vocals_filename}"
    print(f"vocals_filename: {vocals_filename}\nvocals_path: {vocals_path}")

    # Normalize the loudness of the vocals
    normalized_vocals_path = f"{output_destination_file_path}/normalized_vocals.{audio_codec}"
    normalize_audio(vocals_path, normalized_vocals_path)

    # Normalize the loudness of the vocals
    nonsilence_vocals_path = f"{output_destination_file_path}/nonsilence_vocals.{audio_codec}"
    remove_silence(normalized_vocals_path, nonsilence_vocals_path, silence_threshold)

    output_path = input_file.replace('recordings', 'cleaned_recordings').replace('m4a', 'mp3')
    print(f"output_path: {output_path}")
    s3.upload_file(nonsilence_vocals_path, input_bucket_name, output_path)

    print("Completed!")