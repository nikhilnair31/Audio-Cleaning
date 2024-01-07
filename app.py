from spleeter.separator import Separator
from urllib.parse import unquote_plus
import lambdawarmer
import json
import os
import boto3
import logging
import subprocess
from pydub import AudioSegment
from pydub.silence import split_on_silence

silence_threshold = os.environ.get('SILENCE_THRESHOLD')

audio_codec = "mp3"
output_destination = "audio_output"
filename_format = "{instrument}.{codec}"

s3 = boto3.client("s3")

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

            print(f"Downloaded input file to {input_lambda_file_path}, splitting now...")

            os.chdir("/tmp")
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
            remove_silence(vocals_path, nonsilence_vocals_path, silence_threshold)

            output_path = input_file.replace('recordings', 'cleaned_recordings').replace('m4a', 'mp3')
            print(f"output_path: {output_path}")
            s3.upload_file(normalized_vocals_path, input_bucket_name, output_path)

            print("Lambda execution completed!")
        
            return {
                'statusCode': 200,
                'body': json.dumps(output_path)
            }
        except Exception as err:
            print(err)
            raise err