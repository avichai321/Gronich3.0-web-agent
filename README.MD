# Gronich Agent

Gronich Agent is a local desktop application built with PySide6 for KMS stations.

It provides a local operational console for:

- File Copy
- KMS actions
- Data-Link actions

The main operational purpose of the agent in the full system is:

- local use on KMS stations
- File Copy execution from the central server without using SSH into the KMS station

## Main Goals

- Allow users on KMS stations to work locally with a clean desktop GUI
- Keep KMS and Data-Link available locally
- Allow the central server to use the agent only for File Copy jobs
- Support both:
  - Local mode
  - Server-connected mode

## Current Scope

### Local GUI
The agent currently includes:

- Dashboard
- File Copy
- KMS
- Data-Link
- Logs

### Server Integration
The agent can also connect to the backend server for:

- register
- heartbeat
- future File Copy job execution from the server

## Project Structure

```text
gronich3.0-web-agent/
├── main.py
├── requirements.txt
├── assets/
│   └── logo.png
├── config/
│   ├── agent.ini
│   └── local_runtime.ini
├── core/
│   ├── app_state.py
│   ├── config_manager.py
│   ├── logger.py
│   └── api_client.py
├── gui/
│   ├── main_window.py
│   ├── theme.py
│   └── pages/
│       ├── dashboard_page.py
│       ├── file_copy_page.py
│       ├── kms_page.py
│       ├── datalink_page.py
│       └── logs_page.py
├── services/
│   ├── file_copy_service.py
│   ├── kms_service.py
│   ├── datalink_service.py
│   ├── datalink_logic_service.py
│   ├── helpers_service.py
│   ├── parsing_service.py
│   ├── server_sync_service.py
│   └── ssh_service.py
└── logs/