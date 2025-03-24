## Run the following command to start main.py with PM2:
```bash
    pm2 start "python main.py" --name bit_puzzle_bot
```

## To ensure it restarts automatically, run:
```bash
    pm2 save
    pm2 startup
```
## Follow any additional commands PM2 provides to complete setup.