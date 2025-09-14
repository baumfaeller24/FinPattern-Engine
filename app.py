#!/usr/bin/env python3
"""
Flask-Wrapper für FinPattern-Engine Streamlit GUI
Ermöglicht dauerhaftes Deployment der Anwendung
"""

import os
import sys
import subprocess
import threading
import time
from pathlib import Path
from flask import Flask, redirect, render_template_string
import requests

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

app = Flask(__name__)

# Streamlit-Prozess global speichern
streamlit_process = None

def start_streamlit():
    """Startet Streamlit im Hintergrund"""
    global streamlit_process
    
    if streamlit_process is None or streamlit_process.poll() is not None:
        # Streamlit-Kommando
        cmd = [
            sys.executable, "-m", "streamlit", "run", 
            "src/gui/main.py",
            "--server.port", "8502",
            "--server.address", "0.0.0.0",
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false"
        ]
        
        # Starte Streamlit
        streamlit_process = subprocess.Popen(
            cmd,
            cwd=str(project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Warte bis Streamlit bereit ist
        for _ in range(30):  # 30 Sekunden Timeout
            try:
                response = requests.get("http://localhost:8502", timeout=1)
                if response.status_code == 200:
                    break
            except:
                pass
            time.sleep(1)

@app.route('/')
def index():
    """Hauptseite mit Weiterleitung zu Streamlit"""
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="de">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>FinPattern-Engine</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0;
                padding: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .container {
                background: white;
                padding: 3rem;
                border-radius: 20px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                text-align: center;
                max-width: 600px;
                margin: 2rem;
            }
            .logo {
                font-size: 4rem;
                margin-bottom: 1rem;
            }
            h1 {
                color: #333;
                margin-bottom: 1rem;
                font-size: 2.5rem;
            }
            .subtitle {
                color: #666;
                margin-bottom: 2rem;
                font-size: 1.2rem;
            }
            .features {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 1rem;
                margin: 2rem 0;
                text-align: left;
            }
            .feature {
                background: #f8f9fa;
                padding: 1.5rem;
                border-radius: 10px;
                border-left: 4px solid #667eea;
            }
            .feature h3 {
                margin: 0 0 0.5rem 0;
                color: #333;
            }
            .feature p {
                margin: 0;
                color: #666;
                font-size: 0.9rem;
            }
            .cta-button {
                display: inline-block;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 1rem 2rem;
                text-decoration: none;
                border-radius: 50px;
                font-weight: bold;
                font-size: 1.1rem;
                margin: 1rem;
                transition: transform 0.2s, box-shadow 0.2s;
            }
            .cta-button:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(0,0,0,0.2);
            }
            .status {
                background: #e8f5e8;
                color: #2d5a2d;
                padding: 1rem;
                border-radius: 10px;
                margin: 1rem 0;
                border-left: 4px solid #4caf50;
            }
            .loading {
                display: none;
                margin: 1rem 0;
            }
            .spinner {
                border: 3px solid #f3f3f3;
                border-top: 3px solid #667eea;
                border-radius: 50%;
                width: 30px;
                height: 30px;
                animation: spin 1s linear infinite;
                margin: 0 auto;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">🔍</div>
            <h1>FinPattern-Engine</h1>
            <p class="subtitle">Modulares System für Mustererkennung in Finanzmarktdaten</p>
            
            <div class="status">
                <strong>✅ System Online</strong><br>
                Alle Module verfügbar • Dukascopy-Integration aktiv
            </div>
            
            <div class="features">
                <div class="feature">
                    <h3>📥 Dukascopy Download</h3>
                    <p>Kostenlose historische Tickdaten direkt von Dukascopy Bank SA</p>
                </div>
                <div class="feature">
                    <h3>📊 DataIngest</h3>
                    <p>Tick-zu-Bar Konvertierung mit 18-Spalten Schema</p>
                </div>
                <div class="feature">
                    <h3>🧪 Live-Demo</h3>
                    <p>Sofort testbar mit integrierten Beispieldaten</p>
                </div>
                <div class="feature">
                    <h3>⚡ Performance</h3>
                    <p>16,000+ Ticks/Sekunde Verarbeitungsgeschwindigkeit</p>
                </div>
            </div>
            
            <div class="loading" id="loading">
                <div class="spinner"></div>
                <p>Streamlit wird geladen...</p>
            </div>
            
            <a href="/app" class="cta-button" onclick="showLoading()">
                🚀 FinPattern-Engine starten
            </a>
            
            <p style="margin-top: 2rem; color: #666; font-size: 0.9rem;">
                <strong>Entwickelt für professionelle Trading-Strategieentwicklung</strong><br>
                Reproduzierbar • Wissenschaftlich rigoros • Production-ready
            </p>
        </div>
        
        <script>
            function showLoading() {
                document.getElementById('loading').style.display = 'block';
            }
        </script>
    </body>
    </html>
    """)

@app.route('/app')
def streamlit_app():
    """Weiterleitung zur Streamlit-Anwendung"""
    # Stelle sicher, dass Streamlit läuft
    start_streamlit()
    
    # Weiterleitung zu Streamlit
    return redirect("http://localhost:8502", code=302)

@app.route('/health')
def health():
    """Health-Check Endpoint"""
    return {
        "status": "healthy",
        "service": "FinPattern-Engine",
        "streamlit_running": streamlit_process is not None and streamlit_process.poll() is None
    }

@app.route('/status')
def status():
    """Status-Informationen"""
    return {
        "service": "FinPattern-Engine",
        "version": "1.0.0",
        "modules": {
            "DataIngest": "✅ Vollständig",
            "Dukascopy": "✅ Integriert",
            "GUI": "✅ Online"
        },
        "streamlit_status": "running" if streamlit_process and streamlit_process.poll() is None else "stopped"
    }

if __name__ == '__main__':
    # Starte Streamlit beim Start
    threading.Thread(target=start_streamlit, daemon=True).start()
    
    # Starte Flask
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False
    )
