from spleeter.separator import Separator
from urllib.parse import unquote_plus
import lambdawarmer
import json
import os
import boto3
import logging
import requests
import subprocess
from pydub import AudioSegment
from pydub.silence import split_on_silence

# General Related
HUGGINGFACE_API_KEY = str(os.environ.get('HUGGINGFACE_API_KEY'))
HUGGINGFACE_SPEECH_CHANNEL_URL = str(os.environ.get('HUGGINGFACE_SPEECH_CHANNEL_URL'))
SPLIT_AUDIO = os.environ.get('SPLIT_AUDIO', 'False').lower() == 'true'
NORMALIZE_AUDIO = os.environ.get('NORMALIZE_AUDIO', 'False').lower() == 'true'
CLIP_SILENCE = os.environ.get('CLIP_SILENCE', 'False').lower() == 'true'
SILENCE_THRESHOLD = os.environ.get('SILENCE_THRESHOLD')

audio_codec = "mp3"
output_destination = "audio_output"
filename_format = "{instrument}.{codec}"

s3 = boto3.client("s3")

def speech_channels(input_file):
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}

    with open(input_file, "rb") as f:
        data = f.read()
    
    response = requests.post(HUGGINGFACE_SPEECH_CHANNEL_URL, headers=headers, data=data)
    return response.json()

def remove_silence(input_file, output_file):
    # Load the audio file
    audio = AudioSegment.from_file(input_file)

    # Split the audio based on silence
    segments = split_on_silence(audio, silence_thresh=SILENCE_THRESHOLD)

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

def split_audio(input_file):
    os.chdir("/tmp")
    separator = Separator("spleeter:2stems", multiprocess=False)
    print(f"input_file: {input_file}\noutput_destination: {output_destination}\nfilename_format: {filename_format}\naudio_codec: {audio_codec}")
    separator.separate_to_file(input_file, output_destination, filename_format=filename_format, codec=audio_codec, synchronous=True)

@lambdawarmer.warmer
def handler(event, context):
    print("Lambda execution starting!")
    
    is_warmer = event.get("warmer")
    
    if is_warmer:
        print("Lambda function warmed by Cloudwatch rule!")
        return true
    else:
        try:
            # Input
            input_file_obj = event["Records"][0]
            input_bucket_name = str(input_file_obj["s3"]["bucket"]["name"])
            input_file = unquote_plus(str(input_file_obj["s3"]["object"]["key"]))

            # Downloading file to /tmp directory within Lambda
            filename = input_file.split("/")[-1]
            input_lambda_file_path = os.path.join('/tmp', filename)
            print(f"input_bucket_name: {input_bucket_name}\ninput_file: {input_file}\ninput_lambda_file_path: {input_lambda_file_path}")

            # Output
            output_destination_file_path = f"/tmp/{output_destination}"
            print(f"output_destination: {output_destination}\noutput_destination_file_path: {output_destination_file_path}")

            # Downloading file
            s3.download_file(input_bucket_name, input_file, input_lambda_file_path)
            print(f"Downloaded input file to {input_lambda_file_path}")

            # Separated files, identifying vocals file path
            split_unsplit_audio_path = ''
            if SPLIT_AUDIO:
                print(f"Splitting file at {input_lambda_file_path} now...")
                split_audio(input_lambda_file_path)
                split_unsplit_audio_path = f"{output_destination_file_path}/vocals.{audio_codec}"
            else:
                split_unsplit_audio_path = input_lambda_file_path
            print(f"split_unsplit_audio_path: {split_unsplit_audio_path}")

            # Normalize the loudness of the vocals
            normalized_unnormalized_audio_path = ''
            if NORMALIZE_AUDIO:
                print(f"Normalizing file at {split_unsplit_audio_path} now...")
                normalized_unnormalized_audio_path = f"{output_destination_file_path}/normalized_vocals.{audio_codec}"
                normalize_audio(split_unsplit_audio_path, normalized_unnormalized_audio_path)
            else:
                normalized_unnormalized_audio_path = split_unsplit_audio_path
            print(f"normalized_unnormalized_audio_path: {normalized_unnormalized_audio_path}")

            # Normalize the loudness of the vocals
            clipped_unclipped_audio_path = ''
            if CLIP_SILENCE:
                print(f"Clipping file at {normalized_vocals_path} now...")
                clipped_unclipped_audio_path = f"{output_destination_file_path}/nonsilence_vocals.{audio_codec}"
                remove_silence(normalized_vocals_path, clipped_unclipped_audio_path)
            else:
                clipped_unclipped_audio_path = normalized_unnormalized_audio_path
            print(f"clipped_unclipped_audio_path: {clipped_unclipped_audio_path}")

            output_path = input_file.replace('recordings', 'cleaned_recordings').replace('m4a', 'mp3')
            print(f"output_path: {output_path}")
            s3.upload_file(clipped_unclipped_audio_path, input_bucket_name, output_path)

            print("Lambda execution completed!")
        
            return {
                'statusCode': 200,
                'body': json.dumps(output_path)
            }
        except Exception as err:
            print(err)
            raise err