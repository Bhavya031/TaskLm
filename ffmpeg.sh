#!/bin/bash

# FFmpeg GPU Installation Script for NVDEC/NVENC Support
# Optimized for speed - includes only essential components

set -e

echo "Starting FFmpeg installation with NVDEC/NVENC support..."

# Create directories
mkdir -p ~/ffmpeg_sources ~/ffmpeg_build ~/bin

# Update and install minimal dependencies
echo "Installing essential dependencies..."
apt-get update -qq && apt-get -y install \
  autoconf \
  automake \
  build-essential \
  cmake \
  git-core \
  libtool \
  pkg-config \
  wget \
  yasm \
  zlib1g-dev \
  nasm \
  clang \
  lld \
  nvidia-cuda-toolkit \
  nvidia-cuda-dev

echo "Setting up CUDA environment..."
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

echo "Installing NVIDIA codec headers..."
cd ~/ffmpeg_sources
if [ -d "nv-codec-headers" ]; then
    echo "Updating existing nv-codec-headers..."
    cd nv-codec-headers
    git pull
else
    git clone https://git.videolan.org/git/ffmpeg/nv-codec-headers.git
    cd nv-codec-headers
fi
make install PREFIX="$HOME/ffmpeg_build"

echo "Installing minimal x264 for baseline support..."
cd ~/ffmpeg_sources
if [ -d "x264" ]; then
    echo "Updating existing x264..."
    cd x264
    git pull
else
    git clone --depth 1 https://code.videolan.org/videolan/x264.git
    cd x264
fi
PATH="$HOME/bin:$PATH" PKG_CONFIG_PATH="$HOME/ffmpeg_build/lib/pkgconfig" ./configure \
  --prefix="$HOME/ffmpeg_build" \
  --bindir="$HOME/bin" \
  --enable-static \
  --enable-pic \
  --disable-cli
PATH="$HOME/bin:$PATH" make -j$(nproc)
make install

echo "Downloading and compiling FFmpeg..."
cd ~/ffmpeg_sources
if [ -f "ffmpeg-snapshot.tar.bz2" ]; then
    rm ffmpeg-snapshot.tar.bz2
fi
if [ -d "ffmpeg" ]; then
    rm -rf ffmpeg
fi
wget -O ffmpeg-snapshot.tar.bz2 https://ffmpeg.org/releases/ffmpeg-snapshot.tar.bz2
tar xjvf ffmpeg-snapshot.tar.bz2
cd ffmpeg

echo "Configuring FFmpeg with NVIDIA and CUDA support..."
PATH="$HOME/bin:$PATH:/usr/local/cuda/bin" PKG_CONFIG_PATH="$HOME/ffmpeg_build/lib/pkgconfig" ./configure \
  --prefix="$HOME/ffmpeg_build" \
  --pkg-config-flags="--static" \
  --extra-cflags="-I$HOME/ffmpeg_build/include -I/usr/local/cuda/include" \
  --extra-ldflags="-L$HOME/ffmpeg_build/lib -L/usr/local/cuda/lib64" \
  --extra-libs="-lpthread -lm" \
  --bindir="$HOME/bin" \
  --enable-gpl \
  --enable-libx264 \
  --enable-ffnvcodec \
  --enable-cuda-llvm \
  --enable-cuvid \
  --enable-nvdec \
  --enable-nvenc \
  --disable-debug \
  --disable-doc \
  --disable-shared

echo "Compiling FFmpeg (this may take a while)..."
PATH="$HOME/bin:$PATH:/usr/local/cuda/bin" make -j$(nproc)
make install

echo "Installing binaries to /usr/local/bin..."
cp ~/bin/ffmpeg /usr/local/bin/
cp ~/bin/ffprobe /usr/local/bin/

echo "Cleaning up build files to save space..."
rm -rf ~/ffmpeg_sources/ffmpeg ~/ffmpeg_sources/ffmpeg-snapshot.tar.bz2
echo "Keeping nv-codec-headers and x264 for future updates..."

echo "Installation complete!"
echo ""
echo "Testing NVIDIA codec support..."
ffmpeg -hide_banner -encoders | grep nvenc
ffmpeg -hide_banner -decoders | grep cuvid

echo ""
echo "Usage examples:"
echo "# Hardware decode with NVDEC:"
echo "ffmpeg -hwaccel cuda -i input.mp4 output.mp4"
echo ""
echo "# Hardware encode with NVENC:"
echo "ffmpeg -i input.mp4 -c:v h264_nvenc output.mp4"
echo ""
echo "# Full hardware transcode:"
echo "ffmpeg -hwaccel cuda -hwaccel_output_format cuda -i input.mp4 -c:v h264_nvenc output.mp4"
echo ""
echo "# Hardware transcode with GPU scaling:"
echo "ffmpeg -hwaccel cuda -hwaccel_output_format cuda -i input.mp4 -vf scale_cuda=1920:1080 -c:v h264_nvenc output.mp4"
echo ""
echo "FFmpeg with NVDEC/NVENC support is ready!" 