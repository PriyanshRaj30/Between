
# Private Calculator-Based Messaging Application

## 1. Project Overview

This project is a **private two-person messaging application** designed to look and behave like an ordinary calculator when opened.

The application is intended for communication between exactly two authorized people who may be located in different cities. The primary interface is a functional calculator. The messaging functionality is accessible only after entering a predefined secret combination on the calculator.

The goal is to create a minimal communication application where the chat interface is not immediately visible and where messages are protected using modern encryption.

The application will use the internet for communication, allowing the two users to exchange messages regardless of their physical location.

---

# 2. Core Concept

The application has two modes:

### Normal Mode

When the application is opened, the user sees an ordinary calculator:

```text
┌──────────────────────────┐
│                    12345 │
├──────────────────────────┤
│   7    8    9    ÷       │
│   4    5    6    ×       │
│   1    2    3    −       │
│   0    .    =    +       │
└──────────────────────────┘
```

The calculator should actually perform normal mathematical operations.

### Private Mode

The user enters a predetermined secret sequence.

For example:

```text
7 → 3 → 9 → 1 → =
```

If the sequence is correct, the application transitions into the private messaging interface.

```text
┌──────────────────────────┐
│ Private                  │
├──────────────────────────┤
│                          │
│ Her: Are you free?       │
│                          │
│ You: Yeah, what's up?    │
│                          │
├──────────────────────────┤
│ Type a message...    ➤   │
└──────────────────────────┘
```

When the user exits the private mode, the application returns to the calculator.

---

# 3. Two-Person Architecture

This is not intended to be a public messaging platform.

There are only two authorized users:

```text
User A
  │
  │
  ├──── Internet ────┐
  │                  │
  ▼                  ▼
       Backend Server
              │
              │
  ┌───────────┴───────────┐
  │                       │
  ▼                       ▼
User A                  User B
```

Because the two users are in different cities, communication will happen through an internet-accessible backend.

The server acts as a relay and message-storage service.

---

# 4. Communication Protocol

The primary real-time communication protocol will be:

**WebSocket over TLS (`WSS`)**

Normal API operations can use:

**HTTPS**

Architecture:

```text
Mobile Application
       │
       │ HTTPS
       │
       ├──────────────► Authentication
       │
       ├──────────────► Fetch conversation
       │
       └──────────────► Other API operations

Mobile Application
       │
       │ WSS
       ▼
   FastAPI Server
       │
       ▼
   Message Service
       │
       ▼
   PostgreSQL
```

WebSockets are useful because the application can maintain a persistent connection with the server.

When one person sends:

```text
"Are you awake?"
```

the server can immediately deliver the message to the other connected device.

---

# 5. Why WebSocket?

Traditional HTTP polling would require the phone to repeatedly ask:

```text
"Do I have a new message?"

"Do I have a new message?"

"Do I have a new message?"
```

This is inefficient for a chat application.

With WebSockets:

```text
Phone A
   │
   │ persistent connection
   ▼
Server
   │
   │ persistent connection
   ▼
Phone B
```

When a message arrives, the server pushes it to the other device immediately.

This provides near-real-time messaging while keeping the backend relatively simple.

---

# 6. Security Architecture

The secret calculator combination should **not** be considered the actual security mechanism.

It only controls access to the private UI.

The communication itself should be secured independently.

The system should use:

### Transport Encryption

All communication between the phones and server should use TLS:

```text
HTTPS
WSS
```

This prevents network observers from easily reading traffic in transit.

### End-to-End Encryption

For stronger privacy, messages should be encrypted on the sender's device before being sent to the server.

Conceptually:

```text
Plaintext
   │
   ▼
Encryption
   │
   ▼
Ciphertext
   │
   ▼
WSS
   │
   ▼
Server
   │
   ▼
WSS
   │
   ▼
Ciphertext
   │
   ▼
Decryption
   │
   ▼
Plaintext
```

The backend should ideally store only encrypted message content rather than plaintext.

For production-quality encryption, an established protocol/library should be used rather than designing a custom cryptographic protocol.

---

# 7. Message Flow

Suppose User A sends:

> "I reached home."

The process would be:

```text
User A types message
        ↓
Message converted to plaintext
        ↓
Client-side encryption
        ↓
Encrypted message
        ↓
WSS connection
        ↓
FastAPI server
        ↓
Store encrypted message
        ↓
Deliver encrypted message to User B
        ↓
User B decrypts locally
        ↓
"I reached home."
```

The server therefore functions primarily as a **secure relay and storage layer**.

---

# 8. Last Message Feature

One of the key UX requirements is that entering the secret combination should immediately show the most recent conversation state.

For example:

```text
Calculator
    ↓
Secret Combination
    ↓
Private Mode
    ↓

┌──────────────────────────┐
│                          │
│ Her: Did you eat?        │
│                          │
│ You: Not yet 😭          │
│                          │
└──────────────────────────┘
```

The application can retrieve the latest messages from the backend when private mode is opened.

The initial version could display the latest 20–50 messages, while the server retains the complete encrypted conversation history.

---

# 9. Authentication

Only the two registered devices should be able to access the conversation.

A possible setup:

```text
User A
Device A
   │
   └── Unique cryptographic identity

User B
Device B
   │
   └── Unique cryptographic identity
```

There should be no public:

```text
Sign Up
Find Friends
Search Users
Public Profiles
```

Instead, the backend can have exactly two authorized identities.

A device could be registered using a secure pairing process.

---

# 10. Backend

The backend can be written entirely in Python.

### Framework

**FastAPI**

Responsibilities:

- Authentication
- Device registration
- WebSocket connections
- Message routing
- Message persistence
- Encryption metadata handling
- Connection management
- Rate limiting
- Session management

Example architecture:

```text
FastAPI
│
├── auth/
│   ├── authentication
│   └── device_registration
│
├── chat/
│   ├── websocket
│   ├── message_service
│   └── conversation
│
├── crypto/
│   └── key_metadata
│
├── database/
│   ├── models
│   └── repository
│
└── main.py
```

---

# 11. Database

PostgreSQL would be suitable for the production version.

A simplified message table could contain:

```text
messages
────────────────────────
id
conversation_id
sender_id
encrypted_content
created_at
delivered_at
read_at
```

The important point is that:

```text
encrypted_content
```

contains ciphertext rather than the original message.

---

# 12. Mobile Application

There are two possible approaches.

## Python-first approach

Since the project is intended to be developed primarily using Python:

**Kivy / KivyMD**

can be used for the mobile application.

Structure:

```text
mobile/
│
├── calculator/
│   ├── calculator_ui.py
│   └── calculator_logic.py
│
├── private_chat/
│   ├── chat_ui.py
│   └── chat_controller.py
│
├── networking/
│   ├── api_client.py
│   └── websocket_client.py
│
├── security/
│   ├── authentication.py
│   └── encryption.py
│
└── main.py
```

Python would therefore be used for both:

```text
Mobile Application
       +
Backend
```

---

# 13. Application State Machine

The application can be designed as a simple state machine.

```text
              ┌───────────────┐
              │   CALCULATOR  │
              └───────┬───────┘
                      │
                secret sequence
                      │
                      ▼
              ┌───────────────┐
              │ AUTHENTICATE  │
              └───────┬───────┘
                      │
                    valid
                      │
                      ▼
              ┌───────────────┐
              │  PRIVATE CHAT │
              └───────┬───────┘
                      │
                    exit
                      │
                      ▼
              ┌───────────────┐
              │   CALCULATOR  │
              └───────────────┘
```

If an incorrect sequence is entered:

```text
Calculator
    │
    │ incorrect sequence
    ▼
Normal calculator behavior
```

There should be no obvious error indicating that a hidden mode exists.

---

# 14. Offline Behavior

Because the users live in different cities, the application requires internet connectivity for real-time communication.

If the phone temporarily loses connectivity:

```text
Phone
  ↓
No Internet
  ↓
Message queued locally
  ↓
Internet returns
  ↓
Message sent
```

The application can therefore support basic offline message queuing.

---

# 15. Notifications

Notifications require special consideration.

A normal notification such as:

```text
Her sent you a message:
"Are you free?"
```

would defeat the privacy goal.

Instead, notifications could be generic, for example:

```text
Calculator
1 new update
```

or notifications could be disabled entirely.

The actual message should not appear in the notification preview.

---

# 16. Privacy Considerations

The application should minimize information stored on the server.

The backend should avoid storing unnecessary:

- Contact lists
- User profiles
- Location
- Phone contacts
- Message plaintext
- Analytics
- Advertising identifiers

The server primarily needs:

```text
User identity
Device identity
Encrypted messages
Message timestamps
Delivery state
```

Even timestamps should be minimized if maximum privacy is desired.

---

# 17. Initial MVP

The first version does not need every feature.

### Phase 1 — Calculator

- Calculator UI
- Arithmetic operations
- Secret sequence detection
- Switch between calculator/private mode

### Phase 2 — Backend

- FastAPI
- PostgreSQL
- User/device authentication
- HTTPS

### Phase 3 — Chat

- WebSocket
- Send message
- Receive message
- Message history
- Last message display

### Phase 4 — Security

- TLS
- Secure authentication
- Client-side encryption
- Secure key management

### Phase 5 — Mobile Packaging

- Android build
- iOS build if desired
- Secure local storage
- Background notification handling

---

# 18. Proposed Technology Stack

| Component               | Technology                                  |
| ----------------------- | ------------------------------------------- |
| Mobile UI               | Kivy / KivyMD                               |
| Programming Language    | Python                                      |
| Backend                 | FastAPI                                     |
| REST API                | HTTPS                                       |
| Real-time communication | WebSocket / WSS                             |
| Database                | PostgreSQL                                  |
| Local storage           | SQLite / secure device storage              |
| Authentication          | Device-based authentication                 |
| Encryption              | Established E2E encryption protocol/library |
| Deployment              | Linux VPS / cloud server                    |
| Reverse Proxy           | Nginx                                       |
| Containerization        | Docker                                      |

---

# 19. Final Architecture

```text
                 ┌─────────────────────┐
                 │    User A Phone     │
                 │                     │
                 │   Calculator UI     │
                 │         ↓           │
                 │   Secret Sequence   │
                 │         ↓           │
                 │   Private Chat      │
                 └──────────┬──────────┘
                            │
                           WSS
                            │
                            ▼
                 ┌─────────────────────┐
                 │      NGINX          │
                 │    TLS / Proxy      │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │      FastAPI        │
                 │                     │
                 │ Authentication      │
                 │ WebSocket Server    │
                 │ Message Routing     │
                 └──────────┬──────────┘
                            │
                    ┌───────┴───────┐
                    ▼               ▼
              PostgreSQL       Message Service
                    │               │
                    └───────┬───────┘
                            │
                           WSS
                            │
                            ▼
                 ┌─────────────────────┐
                 │    User B Phone     │
                 │                     │
                 │   Calculator UI     │
                 │         ↓           │
                 │   Secret Sequence   │
                 │         ↓           │
                 │   Private Chat      │
                 └─────────────────────┘
```

## 20. Project Objective

The final application should feel like a **normal calculator first and a private communication application second**.

The calculator should remain completely usable as a calculator. The private messaging functionality should only become available after successful authentication through the agreed interaction.

The two users can therefore communicate over the internet from different cities while the application maintains a minimal interface and uses proper cryptographic security for the actual messages.

The most important design principle is:

**Concealment should come from the UI; confidentiality should come from cryptography.**
