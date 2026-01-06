# TikTok Booster (Zefoy)

The Zefoy tab provides integration with Zefoy.com for boosting TikTok metrics. Automate views, likes, shares, and more for your TikTok videos.

## What is Zefoy?

Zefoy is a third-party service that provides free engagement for TikTok content. GhostStorm automates the interaction with Zefoy to boost your videos.

## Available Services

| Service | Description |
|---------|-------------|
| **Followers** | Increase follower count |
| **Hearts** | Add likes to videos |
| **Comment Hearts** | Like comments |
| **Views** | Boost video views |
| **Shares** | Increase share count |
| **Favorites** | Add to favorites |
| **Live Stream** | Live stream viewers |

**Note**: Service availability varies. Click **Check Status** to see which services are currently working.

## Configuration

### TikTok Video URL

Enter the full TikTok video URL:
```
https://www.tiktok.com/@username/video/1234567890123456789
```

### Service Selection

Click to select one or more services to run:
- Selected services highlight in pink
- Multiple services can run sequentially

### Run Settings

| Setting | Description | Recommended |
|---------|-------------|-------------|
| **Repeat Count** | Times to repeat the boost | 1-10 |
| **Delay** | Seconds between repeats | 60+ |
| **Workers** | Parallel sessions | 1-3 |

### Options

| Option | Description |
|--------|-------------|
| **Use Proxies** | Route through proxies (recommended) |
| **Headless Mode** | Run without visible browser |
| **Rotate Proxy** | Different proxy per run |

## Running a Boost

1. **Paste Video URL**: Enter your TikTok video link
2. **Check Service Status**: Click "Check Status" to see available services
3. **Select Services**: Click the services you want
4. **Configure**: Set repeat count and workers
5. **Start**: Click **START BOOSTER**

## Monitoring

### Active Jobs
Shows running boost jobs:
- Service type
- Progress
- Current status

### Recent Logs
Real-time activity:
- Captcha solving
- Service submissions
- Success/failure messages

### Captcha Solver
Status of the OCR captcha solver:
- Green = Ready
- Yellow = Processing
- Red = Error

## How It Works

1. **Navigate to Zefoy**: Browser opens Zefoy.com
2. **Select Service**: Clicks on chosen service tab
3. **Solve Captcha**: OCR reads and submits captcha
4. **Submit URL**: Enters your TikTok link
5. **Wait for Cooldown**: Respects service timer
6. **Repeat**: Continues for set repeat count

## Service Status Colors

When checking status:

| Color | Meaning |
|-------|---------|
| **Green** | Service available |
| **Yellow** | Service has cooldown |
| **Red** | Service unavailable |
| **Gray** | Status unknown |

## Best Practices

### For Best Results

1. **Use Proxies**: Zefoy blocks repeated IPs
2. **Respect Delays**: Don't rush, let cooldowns pass
3. **Start with Views**: Views usually work best
4. **One Service at a Time**: Don't overload
5. **Monitor Logs**: Watch for captcha failures

### Avoiding Blocks

- Enable proxy rotation
- Keep workers low (1-2)
- Use reasonable delays (60+ seconds)
- Don't run 24/7

## Troubleshooting

### "Service Unavailable"
- Zefoy services go up/down frequently
- Try again later or choose different service
- Check Zefoy.com manually to verify

### Captcha Failing
- OCR accuracy varies with image quality
- Retry usually works
- Clear and try again

### IP Blocked
- Enable proxies
- Scrape fresh proxies in Proxies tab
- Wait and retry

### Video URL Invalid
- Ensure full URL is pasted
- URL must be a video, not profile
- Check for typos

### No Results
- Some services have long processing times
- Check TikTok after 5-10 minutes
- Verify the service actually submitted

## Limitations

- Services can be unstable
- Results vary by TikTok algorithm
- Some metrics may not stick
- Zefoy may change their site structure

## Legal Notice

This tool automates interaction with a third-party service. Use responsibly and be aware of TikTok's Terms of Service regarding artificial engagement.

See [Troubleshooting](troubleshooting.md) for more solutions.
