import pandas as pd
import pandas_ta as ta
import yfinance as yf
import matplotlib.pyplot as plt

# 1. Téléchargement avec nettoyage d'index immédiat
ticker = "STLAP.PA"
df = yf.download(ticker, start="2025-10-01", auto_adjust=True)

# CORRECTION MULTI-INDEX : On aplatit les colonnes si yfinance en a créé plusieurs niveaux
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)

# 2. Calcul du RSI (ajouté directement au df)
df['RSI'] = ta.rsi(df['Close'], length=14)

# 3. Calcul du MACD avec 'append=True'
# Cela ajoute MACD_12_26_9, MACDs_12_26_9 et MACDh_12_26_9 directement dans df
df.ta.macd(fast=12, slow=26, signal=9, append=True)

# 4. Nettoyage des lignes de "chauffe" (NaN)
df.dropna(inplace=True)

# 2. Création de la figure
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10), sharex=True, 
                                     gridspec_kw={'height_ratios': [2, 1, 1]})

# --- Graphique 1 : Prix de clôture ---
ax1.plot(df.index, df['Close'], label='Prix (AAPL)', color='black', lw=1.5)
ax1.set_title('Analyse Technique ' + ticker)
ax1.legend(loc='upper left')
ax1.grid(alpha=0.3)

# --- Graphique 2 : RSI ---
ax2.plot(df.index, df['RSI'], label='RSI', color='purple')
ax2.axhline(70, color='red', linestyle='--', alpha=0.5) # Surachat
ax2.axhline(30, color='green', linestyle='--', alpha=0.5) # Survente
ax2.set_ylabel('RSI')
ax2.set_ylim(0, 100)
ax2.grid(alpha=0.3)

# --- Graphique 3 : MACD ---
ax3.plot(df.index, df['MACD_12_26_9'], label='MACD', color='blue')
ax3.plot(df.index, df['MACDs_12_26_9'], label='Signal', color='orange')
ax3.bar(df.index, df['MACDh_12_26_9'], label='Hist', color='gray', alpha=0.3)
ax3.set_ylabel('MACD')
ax3.legend(loc='upper left')
ax3.grid(alpha=0.3)

plt.tight_layout()
plt.show()