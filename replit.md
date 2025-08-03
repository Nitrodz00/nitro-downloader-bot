# Telegram Media Downloader Bot

## Overview

A comprehensive Telegram bot that enables users to download high-quality media content from multiple social media platforms including TikTok, YouTube, Instagram, Twitter/X, and Facebook. The bot features a referral system that provides unlimited downloads to users who invite friends and follow the associated channel. Users can send platform URLs directly to the bot and receive downloaded media files through Telegram's messaging system.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Bot Framework
- **Python-telegram-bot library**: Provides the core framework for handling Telegram API interactions, message processing, and user commands through an asyncio-based architecture
- **Handler-based routing**: Implements separate handlers for commands (/start, /referral), message processing, and callback queries to manage different user interactions
- **Database-driven user management**: SQLite database tracks user information, download counts, referral relationships, and channel follow status

### Media Processing Pipeline
- **Multi-platform downloader architecture**: Separate downloader classes for different platforms, with InstagramDownloader handling Instagram-specific content and yt-dlp handling other platforms
- **URL detection and routing**: Automatic platform detection from URLs using regex patterns to route requests to appropriate download handlers
- **Dual download strategy**: Uses both yt-dlp and instaloader for Instagram content to maximize success rates and handle platform-specific restrictions

### User Management & Permissions
- **Freemium model**: Users receive 5 free downloads initially, with unlimited access granted through referral completion
- **Referral verification system**: Tracks referrals and requires both channel following and successful referral completion for unlimited access
- **Activity-based verification**: Referrals are verified only when referred users demonstrate actual bot usage through downloads

### Data Storage
- **SQLite database**: Three-table schema managing users (download counts, unlimited status), referrals (verification status, relationships), and channel follows (membership tracking)
- **User activity tracking**: Records join dates, last activity, download usage, and referral verification status
- **Referential integrity**: Foreign key relationships between users and referrals maintain data consistency

### Rate Limiting & Access Control
- **Download quota enforcement**: Prevents abuse by limiting free users to 5 downloads total, not per time period
- **Channel membership verification**: Real-time verification of required channel following using Telegram API
- **Admin privilege system**: Configurable admin user IDs for bot management and oversight

### Error Handling & Reliability
- **Comprehensive logging**: Structured logging throughout the application for debugging and monitoring
- **Graceful degradation**: Multiple fallback methods for Instagram downloads and platform-specific error handling
- **Safe messaging**: Utility functions for safe message sending and editing with error recovery

## External Dependencies

### Core Libraries
- **python-telegram-bot**: Primary framework for Telegram Bot API integration and user interaction handling
- **yt-dlp**: Advanced media extraction library supporting YouTube, TikTok, Twitter, Facebook, and other platforms
- **instaloader**: Specialized Instagram content downloader for handling Instagram-specific authentication and content access

### Database
- **SQLite3**: Embedded database for user management, referral tracking, and channel follow verification without external database server requirements

### Media Processing
- **requests**: HTTP client library for API calls and content fetching from social media platforms
- **re (regex)**: URL pattern matching and content extraction for platform detection and shortcode extraction

### System Integration
- **os**: Environment variable management for bot tokens and system file operations
- **logging**: Application monitoring and debugging through structured log output
- **datetime**: Timestamp management for user activity tracking and referral verification
- **asyncio**: Asynchronous operation support for concurrent user request handling