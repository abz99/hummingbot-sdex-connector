#!/bin/bash

# Fix terminal colors in Claude Code
export TERM=xterm-256color
export COLORTERM=truecolor
export FORCE_COLOR=1
export CLICOLOR=1
export CLICOLOR_FORCE=1

# Set up color aliases
alias ls='ls --color=always'
alias ll='ls -la --color=always'
alias grep='grep --color=always'
alias egrep='egrep --color=always'
alias fgrep='fgrep --color=always'

# Git colors
git config --global color.ui always
git config --global color.branch always
git config --global color.diff always
git config --global color.interactive always
git config --global color.status always

# Add to bashrc if not already there
if ! grep -q "FORCE_COLOR=1" ~/.bashrc 2>/dev/null; then
    echo "# Color settings for Claude Code" >> ~/.bashrc
    echo "export TERM=xterm-256color" >> ~/.bashrc
    echo "export COLORTERM=truecolor" >> ~/.bashrc
    echo "export FORCE_COLOR=1" >> ~/.bashrc
    echo "export CLICOLOR=1" >> ~/.bashrc
    echo "export CLICOLOR_FORCE=1" >> ~/.bashrc
    echo "alias ls='ls --color=always'" >> ~/.bashrc
    echo "alias ll='ls -la --color=always'" >> ~/.bashrc
    echo "alias grep='grep --color=always'" >> ~/.bashrc
fi

echo "Color settings applied. Source this file or restart your terminal."
echo "Test with: ls --color=always"