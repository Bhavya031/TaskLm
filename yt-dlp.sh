#!/bin/bash

# Update and install required packages
apt update && apt install -y curl git python3-pip

# Download latest Neovim release
curl -LO https://github.com/neovim/neovim/releases/latest/download/nvim-linux-x86_64.tar.gz

# Remove any existing Neovim in /opt
rm -rf /opt/nvim

# Extract Neovim to /opt
tar -C /opt -xzf nvim-linux-x86_64.tar.gz

# Add Neovim to PATH in .bashrc
echo 'export PATH="$PATH:/opt/nvim-linux-x86_64/bin"' >> ~/.bashrc

# Install Starship prompt
curl -sS https://starship.rs/install.sh | sh

# Initialize Starship in bash
echo 'eval "$(starship init bash)"' >> ~/.bashrc

# Install yt-dlp using pip and also overwrite with latest binary
pip install -U yt-dlp
curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp
chmod +x /usr/local/bin/yt-dlp

# Ensure ~/.config directory exists
mkdir -p ~/.config

# Clone your Neovim config into ~/.config/nvim
git clone https://github.com/Bhavya031/nvim ~/.config/nvim

# Apply all shell changes
source ~/.bashrc