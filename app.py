from spleeter.separator import Separator
from urllib.parse import unquote_plus
import lambdawarmer
import json
import os
import boto3
import logging
import subprocess
from pydub import AudioSegment

s3 = boto3.client("s3")

target_dBFS = os.environ.get("TARGET_DBFS")
audio_codec = "mp3"
output_destination = "audio_output"
filename_format = "{instrument}.{codec}"

def normalize_audio(input_file, output_file):
    # Load the audio file using pydub
    audio = AudioSegment.from_file(input_file)

    # Normalize the loudness to -20 dBFS
    normalized_audio = audio.normalize(target_dBFS=target_dBFS)

    # Export the normalized audio to the output file
    normalized_audio.export(output_file, format=audio_codec)

def remove_silence(input_file, output_file):
    # Load the audio file using pydub
    audio = AudioSegment.from_file(input_file)

    # Convert the audio to 16-bit PCM format
    pcm_data = audio.raw_data
    sample_width = audio.sample_width * 8
    sample_rate = audio.frame_rate
    vad = webrtcvad.Vad()
    vad.set_mode(1)  # Aggressive mode for better voice detection

    # Apply VAD to the audio data
    samples = audio.raw_data
    is_speech = [vad.is_speech(samples[i:i + 2], sample_rate) for i in range(0, len(samples), 2)]

    # Trim silent portions
    trimmed_audio = audio._spawn(b''.join([samples[i:i + 2] for i in range(0, len(samples), 2) if is_speech[i // 2]]))

    # Export the trimmed audio to the output file
    trimmed_audio.export(output_file, format=audio_codec)

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

            # Apply VAD to remove silent portions
            vad_output_path = f"{output_destination_file_path}/vad_vocals.{audio_codec}"
            remove_silence(vocals_path, vad_output_path)

            # Normalize the loudness of the vocals
            normalized_vocals_path = f"{output_destination_file_path}/normalized_vocals.{audio_codec}"
            normalize_audio(vad_output_path, normalized_vocals_path)

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