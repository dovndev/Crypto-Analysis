import ccxt.async_support as ccxt  # Use async support
import asyncio
import pandas as pd
import ta
from flask import Flask, render_template_string

app = Flask(__name__)

# Initialize Binance exchange (async version)

exchange = ccxt.kucoin()  # Change from ccxt.binance() to ccxt.kucoin()


async def get_all_pairs():
    # Fetch all markets available on Binance
    markets = await exchange.load_markets()
    # Filter out USDT pairs
    usdt_pairs = [symbol for symbol in markets if '/USDT' in symbol]
    return usdt_pairs

async def analyze_crypto(symbol):
    try:
        # Fetch OHLCV data and compute indicators
        timeframe = '1h'
        limit = 100
        ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        # Fetch the current price
        ticker = await exchange.fetch_ticker(symbol)
        current_price = ticker['last']  # Get the last traded price

        # Calculate Indicators
        df['RSI'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
        df['MACD'] = ta.trend.MACD(df['close']).macd()
        df['MACD_signal'] = ta.trend.MACD(df['close']).macd_signal()
        df['SMA_50'] = df['close'].rolling(window=50).mean()
        df['SMA_200'] = df['close'].rolling(window=200).mean()
        df['ADX'] = ta.trend.ADXIndicator(df['high'], df['low'], df['close'], window=14).adx()
        bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
        df['BB_upper'] = bb.bollinger_hband()
        df['BB_lower'] = bb.bollinger_lband()

        # Extract values
        last_close = df['close'].iloc[-1]
        current_rsi = df['RSI'].iloc[-1]
        current_macd = df['MACD'].iloc[-1]
        current_macd_signal = df['MACD_signal'].iloc[-1]
        current_adx = df['ADX'].iloc[-1]
        current_sma_50 = df['SMA_50'].iloc[-1]
        current_sma_200 = df['SMA_200'].iloc[-1]
        bb_upper = df['BB_upper'].iloc[-1]
        bb_lower = df['BB_lower'].iloc[-1]

        # Define trade action
        crypto_data = {
            "symbol": symbol,
            "current_price": current_price,
            "rsi": f"{current_rsi:.2f}",
            "macd": f"{current_macd:.2f}",
            "adx": f"{current_adx:.2f}",
            "sma_50": f"{current_sma_50:.2f}",
            "sma_200": f"{current_sma_200:.2f}"
        }

        # Define action
        if current_rsi < 40 or last_close <= bb_lower:
            action = "BUY ✅"
        elif current_rsi > 60 or last_close >= bb_upper:
            action = "SELL ❌"
        else:
            action = "HOLD 🤔"
        
        return crypto_data, action
    except ccxt.BaseError as e:
        print(f"Error processing {symbol}: {str(e)}")
        return None, "Error"
    except Exception as e:
        print(f"General error processing {symbol}: {str(e)}")
        return None, "Error"

async def run_python_program():
    result = []
    all_pairs = await get_all_pairs()  # Get all USDT pairs

    tasks = []
    for symbol in all_pairs:
        tasks.append(analyze_crypto(symbol))

    results = await asyncio.gather(*tasks)

    for i, (crypto_data, action) in enumerate(results):
        if crypto_data:
            result.append({"crypto": crypto_data, "action": action})
        else:
            print(f"Skipping invalid symbol due to error.")

    return result

@app.route('/')
async def home():
    # Run the Python program and get the result
    program_output = await run_python_program()

    # Render the result in a simple HTML template
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Crypto Analysis</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { background-color: #1e1e1e; color: #ffffff; font-family: 'Arial', sans-serif; }
            .card-body { padding: 20px; }
            .table th, .table td { vertical-align: middle; text-align: center; }
            .crypto-card { margin-bottom: 20px; border-radius: 15px; background-color: #2a2a2a; color: white; }
            .btn-buy { background-color: #28a745; color: white; font-weight: bold; }
            .btn-sell { background-color: #dc3545; color: white; font-weight: bold; }
            .btn-hold { background-color: #ffc107; color: black; font-weight: bold; }
            .btn { width: 100%; padding: 10px; font-size: 16px; }
            
            /* Loading spinner */
            #loading {
                display: block;
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                z-index: 9999;
                font-size: 24px;
                color: white;
            }
            
            .spinner {
                border: 8px solid #f3f3f3; 
                border-top: 8px solid #3498db; 
                border-radius: 50%;
                width: 50px;
                height: 50px;
                animation: spin 1s linear infinite;
            }

            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        </style>
    </head>
    <body>
        <div id="loading">
            <div class="spinner"></div>
            <p>Loading data...</p>
        </div>

        <div class="container" id="content" style="display: none;">
            <div class="row mt-5">
                <div class="col-12 text-center mb-4">
                    <h1>📊 Crypto Trading Signals</h1>
                    <p>Real-time analysis of cryptocurrency markets to assist in trading decisions.</p>
                </div>

                {% for item in program_output %}
                <div class="col-md-4 mb-4">
                    <div class="card crypto-card">
                        <div class="card-header">
                            <h4>{{ item.crypto.symbol }}</h4>
                            <p class="text-muted">{{ item.crypto.symbol.split('/')[0] }} - Cryptocurrency</p>
                        </div>
                        <div class="card-body">
                            <p><strong>Current Price:</strong> ${{ item.crypto.current_price }}</p>
                            <p><strong>RSI:</strong> {{ item.crypto.rsi }}</p>
                            <p><strong>MACD:</strong> {{ item.crypto.macd }}</p>
                            <p><strong>ADX:</strong> {{ item.crypto.adx }}</p>
                            <p><strong>SMA 50:</strong> {{ item.crypto.sma_50 }}</p>
                            <p><strong>SMA 200:</strong> {{ item.crypto.sma_200 }}</p>
                            <a href="#" class="btn 
                                {% if 'BUY' in item.action %}btn-buy{% elif 'SELL' in item.action %}btn-sell{% else %}btn-hold{% endif %}">
                                {{ item.action }}
                            </a>
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>

        <script>
            window.onload = function() {
                // Hide the loading spinner
                document.getElementById("loading").style.display = "none";
                // Show the content
                document.getElementById("content").style.display = "block";
            }
        </script>

        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """
    
    return render_template_string(html_template, program_output=program_output)

if __name__ == '__main__':
    app.run(debug=True)
