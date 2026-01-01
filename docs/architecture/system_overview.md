# System Architecture: Decoupled Supervisor Pattern

This document outlines the architecture for the **Personal Documents Handler**, specifically the embedding pipeline. It utilizes a "Supervisor" pattern to manage memory leaks and optimize hardware usage on Apple Silicon.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#2D3436', 'primaryTextColor': '#fff', 'primaryBorderColor': '#727b7f', 'lineColor': '#F8F8F2', 'secondaryColor': '#006100', 'tertiaryColor': '#fff'}}}%%

graph TD
    %% --- HOST SYSTEM LAYER ---
    subgraph Host ["🖥️ macOS Host - Apple Silicon"]
        style Host fill:#2d3436,stroke:#636e72,stroke-width:2px,color:#fff
        
        RawFiles[📂 Documents<br/><i>PDF / Images</i>]:::file
        SysMon[⚙️ Hardware<br/><i>CPU & RAM</i>]:::hardware
    end

    %% --- APP LAYER ---
    subgraph App ["🚀 Personal Docs Handler"]
        style App fill:#353b48,stroke:#7f8fa6,stroke-width:2px,color:#fff

        %% ORCHESTRATOR
        subgraph Supervisor [The Orchestrator]
            style Supervisor fill:#2f3640,stroke:#dcdde1,stroke-dasharray: 5 5,color:#fff
            
            MainLoop{Main Event Loop}:::logic
            Sniper[🔫 Sniper<br/><i>RAM Monitor</i>]:::alert
            Scaler[⚖️ Auto-Scaler<br/><i>CPU Monitor</i>]:::alert
            BatchEmbed[🧠 Embedder<br/><i>SentenceTransformer</i>]:::ai
        end

        %% UI THREAD
        subgraph UI [Frontend Thread]
            style UI fill:#2f3640,stroke:#dcdde1,stroke-dasharray: 5 5,color:#fff
            Dashboard[🖥️ Dashboard<br/><i>Tkinter GUI</i>]:::ui
        end

        %% IPC
        subgraph IPC [Inter-Process Comms]
            style IPC fill:#353b48,stroke:none,color:#fff
            TaskQ(Task Queue):::queue
            ResultQ(Result Queue):::queue
        end

        %% WORKERS
        subgraph Pool ["Process Pool (5-12 Workers)"]
            style Pool fill:#2f3640,stroke:#44bd32,stroke-width:2px,color:#fff
            
            W1[👷 Worker 1]:::worker
            W2[👷 Worker 2]:::worker
            W_dots[...]:::worker
            W_N[👷 Worker N]:::worker
        end
    end

    %% --- STORAGE LAYER ---
    subgraph DB [Persistent Storage]
        style DB fill:#2d3436,stroke:#636e72,stroke-width:2px,color:#fff
        LanceDB[(🗄️ LanceDB<br/><i>Vector Store</i>)]:::db
    end

    %% --- LOGIC FLOWS ---
    
    %% 1. Ingestion
    RawFiles ==>|1. Scan| MainLoop
    MainLoop ==>|2. Push| TaskQ
    TaskQ -.->|Pop| W1 & W2 & W_N

    %% 2. Worker Processing
    W1 -->|3. Status Update| ResultQ
    
    %% 3. Result Handling
    ResultQ -->|4. Read| MainLoop
    MainLoop -->|5a. Update| Dashboard
    MainLoop --Data--> BatchEmbed
    BatchEmbed ==>|5b. Write| LanceDB

    %% 4. Supervision
    Sniper -.->|Kill > 4GB| W1
    Scaler -.->|Monitor| SysMon
    Scaler --Spawn if <50%--> Pool

    %% --- STYLING CLASSES ---
    classDef file fill:#0984e3,stroke:#74b9ff,stroke-width:2px,color:#fff;
    classDef hardware fill:#636e72,stroke:#b2bec3,stroke-width:2px,color:#fff;
    classDef logic fill:#6c5ce7,stroke:#a29bfe,stroke-width:2px,color:#fff;
    classDef alert fill:#d63031,stroke:#ff7675,stroke-width:2px,color:#fff;
    classDef ai fill:#e17055,stroke:#fab1a0,stroke-width:2px,color:#fff;
    classDef ui fill:#00b894,stroke:#55efc4,stroke-width:2px,color:#fff;
    classDef queue fill:#fdcb6e,stroke:#ffeaa7,stroke-width:2px,color:#333;
    classDef worker fill:#00cec9,stroke:#81ecec,stroke-width:2px,color:#333;
    classDef db fill:#6c5ce7,stroke:#a29bfe,stroke-width:4px,color:#fff;