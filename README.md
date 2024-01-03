# MIA-Audio-Pre-Lambda

This repo can be built to create an image (3.35G uncompressed, 1.31G compressed) that can be used to run Spleeter, FFMPEG, and Python 3.7 on an AWS Lambda function. It comes pre-built with Spleeter's 2 stem pretrained models to split an input audio track into accompaniment and vocal output tracks.

## Getting Started:

1. Run `deploy.ps1`

## Lambda Set Up
1. OPTIONAL: You can set up an AWS EventBridge Cloudwatch Event rule to ping your lambda function (e.g. every 5 minutes) to keep it warm. This rule should send the following as a constant JSON parameter to be consumed by [lambda-warmer-py](https://github.com/robhowley/lambda-warmer-py):
```json
{
  "warmer": true,
  "concurrency": 1
}
```
2. Set up an S3 trigger on your Lambda function using an S3 input audio bucket so that it is invoked when audio is uploaded to that bucket.
