# VMS Offline Version — Database Setup Guide

This guide walks you through setting up the local PostgreSQL database
required to run the standalone (offline) Visitor Management System (VMS)
using pgAdmin 4.

---

## Overview

The offline version of VMS connects to a local PostgreSQL database instead
of a cloud-hosted one. Before running the app for the first time, you need
to create an **empty** database with a specific name — the app builds all
the tables automatically the first time it runs.

---

## Prerequisites

Before you begin, make sure you have:

- [ ] **PostgreSQL** installed and running as a background service on your machine
- [ ] **pgAdmin 4** installed (comes bundled with most PostgreSQL installers)
- [ ] Your PostgreSQL **master password** (set during installation)

> **Tip:** To check PostgreSQL is running on Windows, open the Services app
> and look for "postgresql-x64-\<version\>" with a status of "Running."

---

## Step 1: Connect to Your Local Server

1. Open **pgAdmin 4**.
2. In the left-hand **Browser** panel, expand **Servers**.
3. Click your local PostgreSQL server (e.g., **PostgreSQL 14** or
   **PostgreSQL 15** — the exact name depends on your installed version).
4. When prompted, enter your PostgreSQL master password to connect.

---

## Step 2: Create the Database

The app looks for a database with an exact, specific name. **The app will
fail to start if this database doesn't exist or is misnamed.**

1. Right-click **Databases** in the left sidebar.
2. Select **Create > Database...**
3. In the **Database** field, enter exactly:

   ```
   Vms-offline
   ```

   > ⚠️ **This name is case-sensitive.** The capital `V` must match exactly,
   > or the application won't be able to find the database.

4. Leave all other fields at their defaults and click **Save**.
5. Confirm `Vms-offline` now appears under **Databases** in the tree.

---

## Step 3: Confirm Connection Settings

The app's database configuration expects these default local PostgreSQL
settings. Double-check they match your setup:

| Setting          | Expected Value  |
|-------------------|-----------------|
| Host              | `127.0.0.1` (localhost) |
| Port              | `5432`          |
| Database name     | `Vms-offline`   |

If your PostgreSQL installation uses a different port or a custom
username/password, you'll need to update the connection string in the
app's configuration file (e.g., `.env` or `config.py`) to match — otherwise
the app won't be able to connect.

---

## Step 4: Run the App to Build the Schema

You don't need to manually create any tables — the app builds the full
database schema (Visitors, Visitor Logs, Users, Requests) automatically
the first time it connects.

1. Open a terminal in the project's root directory.
2. Run the application:

   ```
   python run.py
   ```

   or, if you're debugging:

   ```
   python debug_run.py
   ```

3. On success, the terminal should show the app starting without database
   errors. Refresh `Vms-offline` in pgAdmin — you should now see the
   generated tables listed under **Schemas > public > Tables**.

---

## Troubleshooting

| Problem | Likely Cause | Fix |
|---|---|---|
| App fails to start with a "database does not exist" error | Database name doesn't match exactly | Re-check spelling and capitalization: `Vms-offline` |
| Connection refused / can't connect | PostgreSQL service isn't running | Start the PostgreSQL service from Services (Windows) or `pg_ctl`/`systemctl` (Mac/Linux) |
| Authentication failed | Wrong password, or config doesn't match your local credentials | Update the connection string in your `.env`/config file |
| App runs but no tables appear | The database wasn't empty, or the app didn't complete its first run | Drop and recreate `Vms-offline`, then re-run the app |

---

## Quick Checklist

- [ ] PostgreSQL is installed and running
- [ ] pgAdmin 4 is installed and connected to the local server
- [ ] `Vms-offline` database created (exact spelling/casing)
- [ ] Host/port match `127.0.0.1:5432` (or config updated to match your setup)
- [ ] App run once successfully to auto-generate tables
