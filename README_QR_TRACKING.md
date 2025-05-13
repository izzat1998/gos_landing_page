# QR Code Tracking System with Telegram Bot Integration

This guide explains how to use the QR code tracking system for your Django landing page, including how to set up the Telegram bot for statistics.

## Overview

The QR code tracking system allows you to:

1. Create QR codes for different physical locations
2. Track visits when customers scan these QR codes
3. View detailed statistics in the admin panel
4. Access statistics via a Telegram bot, including an interactive dashboard

## Setup Instructions

### 1. Install Required Packages

Make sure all required packages are installed:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Run Migrations

Apply the database migrations to create the necessary tables:

```bash
python manage.py makemigrations
python manage.py migrate
```

### 3. Create a Superuser (if you haven't already)

```bash
python manage.py createsuperuser
```

### 4. Generate API Token for Telegram Bot

```bash
python manage.py create_api_token admin  # Replace 'admin' with your superuser username
```

Copy the generated token and update your `.env` file:

```
API_TOKEN=your_generated_token_here
```

### 5. Create Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Send the `/newbot` command and follow the instructions
3. Copy the bot token provided by BotFather
4. Update your `.env` file:

```
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

### 6. Configure Admin Telegram Usernames

Open `/main/management/commands/run_telegram_bot.py` and update the `ADMIN_USERNAMES` list with your Telegram username:

```python
ADMIN_USERNAMES = ['your_telegram_username']  # Add your Telegram username here
```

### 7. Update Site URL

In your `.env` file, update the `SITE_URL` with your actual site URL:

```
SITE_URL=https://your-actual-site.com  # For production
# or
SITE_URL=http://localhost:8000  # For local development
```

## Using the System

### Creating Locations

1. Log in to the Django admin panel (`/admin/`)
2. Go to "Locations" under the "Main" app
3. Click "Add Location" and fill in the details
4. Save the location

### Generating QR Codes

1. In the admin panel, go to the Locations list
2. For each location, you'll see a "View QR Code" button
3. Click to view and download the QR code
4. Alternatively, visit `/qrcodes/` to see all QR codes in one place

### Viewing Statistics in Admin Panel

1. In the admin panel, go to the Locations list
2. For each location, click the "View Stats" button
3. You'll see detailed statistics including:
   - Today's scans
   - Yesterday's scans
   - Last 7 days
   - Last 30 days
   - Total scans
   - Hourly distribution chart

### Using the Telegram Bot

1. Start the Telegram bot:

```bash
python manage.py run_telegram_bot
```

2. Open Telegram and search for your bot by username
3. Start a conversation with your bot by sending `/start`

#### Regular User Commands

- `/start` - Welcome message and available commands
- `/help` - Show help message
- `/stats` - View basic statistics for all locations
- `/stats 7` - View statistics for the last 7 days

#### Admin Commands (only for users in ADMIN_USERNAMES)

- `/admin` - Show admin commands
- `/allstats` - View detailed statistics for all locations
- `/allstats 7` - View all stats for the last 7 days
- `/compare` - Compare statistics between locations
- `/dashboard` - Interactive dashboard with buttons for different statistics views

## Testing QR Codes

To test a QR code without printing it:

1. In the admin panel, go to the statistics page for a location
2. Use the provided test URL to simulate a scan
3. Refresh the statistics page to see the updated counts

## Troubleshooting

### Bot Not Responding

- Check that the bot token in `.env` is correct
- Ensure the Telegram bot is running (`python manage.py run_telegram_bot`)
- Verify your internet connection

### API Token Issues

- Regenerate the API token: `python manage.py create_api_token admin`
- Update the `.env` file with the new token

### Admin Access Issues

- Make sure your Telegram username is correctly added to the `ADMIN_USERNAMES` list
- Telegram usernames are case-sensitive and should not include the '@' symbol

## Security Considerations

- Keep your API token and bot token secure
- Use HTTPS in production for secure QR code scanning
- Consider implementing rate limiting for the QR code scanning endpoint

## Customization

You can customize the system by:

1. Modifying the QR code design in `main/views.py` (LocationQRCodeView)
2. Adding additional statistics in the admin panel
3. Extending the Telegram bot with more commands

For any questions or issues, please contact the development team.
