import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import pickle
import os

# 1. Generate Synthetic Training Data
# Features: [latency_ms, z_score, order_count_per_sec]
# Target: [0 (HEALTHY), 1 (CPU_SPIKE), 2 (NETWORK_DELAY), 3 (MEMORY_LEAK)]

def generate_training_data(n_samples=5000):
    data = []
    
    for _ in range(n_samples):
        # Healthy traffic
        lat = np.random.normal(0.5, 0.1) # 0.5ms mean
        z = (lat - 0.5) / 0.1
        data.append([lat, z, 0]) # 0 = HEALTHY
        
        # CPU Spike (high latency, low Z variance)
        lat = np.random.normal(15.0, 2.0)
        z = (lat - 0.5) / 0.1 
        data.append([lat, z, 1]) # 1 = CPU_SPIKE
        
        # Network Delay (extremely high spikes, high Z)
        lat = np.random.normal(80.0, 10.0)
        z = (lat - 0.5) / 0.1
        data.append([lat, z, 2]) # 2 = NETWORK_DELAY
        
    df = pd.DataFrame(data, columns=['latency_ms', 'z_score', 'label'])
    return df

def train_model():
    print("[Brain-Train] Generating synthetic data...")
    df = generate_training_data()
    X = df[['latency_ms', 'z_score']]
    y = df['label']
    
    print("[Brain-Train] Training Random Forest model...")
    clf = RandomForestClassifier(n_estimators=100)
    clf.fit(X, y)
    
    # Save the model
    os.makedirs('brain/models', exist_ok=True)
    with open('brain/models/classifier.pkl', 'wb') as f:
        pickle.dump(clf, f)
    print("[Brain-Train] Model saved to brain/models/classifier.pkl")

if __name__ == "__main__":
    train_model()
