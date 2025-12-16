# MongoDB Atlas Free Setup Guide

## 🆓 MongoDB Atlas Free Tier
- **Storage**: 512 MB (enough for thousands of trades)
- **Cost**: 100% FREE forever
- **No credit card required**

## 📝 Setup Steps (5 minutes)

### 1. Create MongoDB Atlas Account
1. Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas/register)
2. Sign up with email or Google
3. Choose **FREE** tier (M0 Sandbox)

### 2. Create a Cluster
1. Select **FREE Shared** cluster
2. Choose **AWS** and closest region (e.g., Mumbai/Singapore for India)
3. Cluster Name: `trading-cluster` (or any name)
4. Click **Create Cluster** (takes 3-5 minutes)

### 3. Create Database User
1. Go to **Database Access** (left sidebar)
2. Click **Add New Database User**
3. Choose **Password** authentication
4. Username: `trading-bot`
5. Password: Generate a secure password (save it!)
6. Database User Privileges: **Read and write to any database**
7. Click **Add User**

### 4. Whitelist IP Address
1. Go to **Network Access** (left sidebar)
2. Click **Add IP Address**
3. Click **Allow Access from Anywhere** (0.0.0.0/0)
   - This is needed for Render to connect
4. Click **Confirm**

### 5. Get Connection String
1. Go to **Database** (left sidebar)
2. Click **Connect** on your cluster
3. Choose **Connect your application**
4. Driver: **Python**, Version: **3.12 or later**
5. Copy the connection string, it looks like:
   ```
   mongodb+srv://trading-bot:<password>@trading-cluster.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```
6. Replace `<password>` with your actual password

### 6. Add to Render Environment Variables
1. Go to Render Dashboard
2. Click on your service
3. Go to **Environment** tab
4. Click **Add Environment Variable**
5. Key: `MONGODB_URI`
6. Value: Paste your connection string (with password replaced)
7. Click **Save Changes**

## ✅ Done!
Your strategies will now automatically save trades to MongoDB Atlas!

## 🔍 View Your Data
1. Go to MongoDB Atlas Dashboard
2. Click **Browse Collections**
3. Database: `trading_strategies`
4. Collections:
   - `trades_1min`
   - `trades_5min`
   - `trades_15min`

## 💡 Benefits
- ✅ Data persists forever (even when Render restarts)
- ✅ Access from anywhere
- ✅ Built-in backups
- ✅ Query and analyze trades easily
- ✅ No credit card required
