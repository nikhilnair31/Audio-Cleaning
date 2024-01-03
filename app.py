from spleeter.separator import Separator
from urllib.parse import unquote_plus
import lambdawarmer
import json
import os
import boto3
import logging
import subprocess
import openai

os.environ["NUMBA_CACHE_DIR"] = "/tmp/"
openai_api_key = os.environ.get('OPENAI_API_KEY')

s3 = boto3.client("s3")
openai.api_key = openai_api_key

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
            output_destination = os.environ.get("OUTPUT_DESTINATION") or "audio_output"
            output_destination_file_path = f"/tmp/{output_destination}"
            print(f"output_destination: {output_destination}\noutput_destination_file_path: {output_destination_file_path}")

            # Downloading file
            s3.download_file(input_bucket_name, input_file, input_lambda_file_path)

            print(f"Downloaded input file to {input_lambda_file_path}, splitting now...")

            os.chdir("/tmp")
            audio_codec = os.environ.get("OUTPUT_AUDIO_CODEC") or "mp3"
            filename_format = os.environ.get("OUTPUT_FILENAME_FORMAT") or "{instrument}.{codec}"
            separator = Separator("spleeter:2stems", multiprocess=False)
            print(f"input_lambda_file_path: {input_lambda_file_path}\noutput_destination: {output_destination}\nfilename_format: {filename_format}\naudio_codec: {audio_codec}")
            separator.separate_to_file(input_lambda_file_path, output_destination, filename_format=filename_format, codec=audio_codec, synchronous=True)

            # Separated files, identifying vocals file path
            vocals_filename = f"vocals.{audio_codec}"
            vocals_path = f"{output_destination_file_path}/{vocals_filename}"
            print(f"vocals_filename: {vocals_filename}\nvocals_path: {vocals_path}")

            # Pass the vocals to Whisper for transcription
            transcript_text = ""
            audio_file = open(vocals_path, "rb")
            response = openai.Audio.transcribe(
                "whisper-1", 
                audio_file,
                language="en",
                prompt="don't translate or make up words to fill in the rest of the sentence. if background noise return ."
            )
            transcript_text = response['text']
            print(f"transcript_text: {transcript_text}")

            print("Lambda execution completed!")
        
            return {
                'statusCode': 200,
                'body': json.dumps(transcript_text)
            }
        except Exception as err:
            print(err)
            raise err