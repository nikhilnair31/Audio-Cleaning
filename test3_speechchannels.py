from speechbrain.pretrained import SepformerSeparation as separator
import torchaudio
import os
# from pydub import AudioSegment

# input_filepath = r'audio_cache/recording_06012024233332.m4a'
converted_filepath = r'audio_cache/recording_06012024233332.wav'

# audio = AudioSegment.from_file(input_filepath, format='m4a')
# downsampled_audio = audio.set_frame_rate(8000)
# downsampled_audio.export(converted_filepath, format='wav')

model = separator.from_hparams(
    source="speechbrain/sepformer-wsj02mix", 
    savedir='pretrained_models/sepformer-wsj02mix'
    # run_opts={"device":"cuda"}
)

# est_sources = model.separate_file(path=converted_filepath)

# torchaudio.save("source1hat.wav", est_sources[:, :, 0].detach().cpu(), 8000)
# torchaudio.save("source2hat.wav", est_sources[:, :, 1].detach().cpu(), 8000)

# Calculate the chunk size for a 30-second segment
chunk_duration = 30  # seconds
sample_rate = 8000
chunk_size = int(chunk_duration * sample_rate)

# Process audio in 30-second chunks to reduce memory usage
est_sources_list = []

# Load the downsampled audio file
waveform, _ = torchaudio.load(converted_filepath, normalize=True)

# Calculate the number of chunks
num_chunks = waveform.size(1) // chunk_size

# Create a temporary directory for saving chunks
temp_dir = "temp_chunks"
os.makedirs(temp_dir, exist_ok=True)

for i in range(num_chunks):
    start_idx = i * chunk_size
    end_idx = (i + 1) * chunk_size

    # Extract a chunk
    waveform_chunk = waveform[:, start_idx:end_idx]

    # Save the chunk to the temporary directory
    temp_filepath = rf"{temp_dir}/temp_chunk_{i}.wav"
    torchaudio.save(temp_filepath, waveform_chunk, sample_rate)

    # Model separation on the chunk file
    est_sources_chunk = model.separate_file(path=temp_filepath)

    # Append the separated sources to the list
    est_sources_list.append(est_sources_chunk)

# Concatenate the separated sources from chunks
est_sources = torch.cat(est_sources_list, dim=1)

# Save the separated sources with 8000 Hz sampling rate
torchaudio.save("source1hat.wav", est_sources[:, :, 0].detach().cpu(), 8000)
torchaudio.save("source2hat.wav", est_sources[:, :, 1].detach().cpu(), 8000)

# Delete intermediate variables and temporary files to free up memory
del est_sources_list, est_sources_chunk, est_sources
for i in range(num_chunks):
    temp_filepath = os.path.join(temp_dir, f"temp_chunk_{i}.wav")
    os.remove(temp_filepath)
os.rmdir(temp_dir)