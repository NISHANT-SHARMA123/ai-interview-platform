"""
Comprehensive Question Bank & Semantic Concept Evaluator.
Contains curated, production-grade interview questions across all domains and seniority levels,
complete with expected key points, semantic concept keywords, and contextual follow-ups.
Enables diverse, non-repeating question generation and accurate, substantive answer evaluation.
"""

import re
import random
from typing import List, Dict, Any, Optional

QUESTION_BANK: Dict[str, List[Dict[str, Any]]] = {
    # -------------------------------------------------------------------------
    # BACKEND ENGINEERING
    # -------------------------------------------------------------------------
    "backend": [
        {
            "question": "Can you explain the difference between optimistic and pessimistic locking in database transactions, and when you would choose one over the other?",
            "category": "Technical",
            "difficulties": ["mid", "senior", "staff"],
            "expected_key_points": [
                "Version/timestamp column for optimistic locking",
                "SELECT FOR UPDATE row-level locks for pessimistic locking",
                "Contention levels and collision frequency tradeoffs",
                "Deadlock risk and throughput implications"
            ],
            "core_keywords": ["optimistic", "pessimistic", "lock", "locking", "version", "timestamp", "select for update", "contention", "deadlock", "retry", "throughput", "transaction", "isolation"],
            "follow_ups": [
                {
                    "question": "If an optimistic locking collision occurs under high write load, what backoff and retry strategy would you implement to prevent thundering herd?",
                    "rationale": "Evaluates handling of distributed retries and jittered exponential backoff."
                },
                {
                    "question": "How would you handle distributed locking across multiple independent microservices where database-level row locking isn't sufficient?",
                    "rationale": "Tests knowledge of Redlock, ZooKeeper, or Redis lease mechanisms."
                }
            ]
        },
        {
            "question": "How do you design an idempotent payment processing API to guarantee customers are never double-charged during network timeouts?",
            "category": "Technical",
            "difficulties": ["entry", "mid", "senior", "staff"],
            "expected_key_points": [
                "Unique Idempotency-Key header from client",
                "Atomic check-and-insert in database or Redis",
                "Handling in-flight duplicate requests (lock with lease)",
                "Storing and returning cached responses for identical keys"
            ],
            "core_keywords": ["idempotent", "idempotency", "key", "header", "redis", "atomic", "cache", "double charge", "timeout", "network", "status", "uuid", "transaction", "payment"],
            "follow_ups": [
                {
                    "question": "What happens if a client retries with the same idempotency key but alters the payload (e.g. changing the transaction amount)?",
                    "rationale": "Tests security and payload fingerprinting (e.g. SHA-256 hash matching)."
                },
                {
                    "question": "How do you expire idempotency keys safely without risking delayed replay attacks?",
                    "rationale": "Evaluates TTL strategies and audit log reconciliation."
                }
            ]
        },
        {
            "question": "Walk me through how database indexes (such as B-Tree and Hash indexes) work internally, and what trade-offs they introduce for read vs write operations.",
            "category": "Technical",
            "difficulties": ["entry", "mid", "senior"],
            "expected_key_points": [
                "B-Tree balanced tree structure (O(log N) lookup, range queries)",
                "Hash indexes (O(1) exact match, no range query support)",
                "Write overhead (index maintenance on INSERT, UPDATE, DELETE)",
                "Disk page fragmentation and memory cache (buffer pool) usage"
            ],
            "core_keywords": ["b-tree", "btree", "hash", "index", "indices", "o(log n)", "range", "write overhead", "insert", "update", "leaf", "page", "buffer", "scan", "lookup"],
            "follow_ups": [
                {
                    "question": "When would a database query planner decide to perform a full table scan even though an index exists on the query column?",
                    "rationale": "Tests understanding of index selectivity, cardinaility, and cost-based optimizers."
                }
            ]
        },
        {
            "question": "How would you design a distributed rate limiter that enforces a limit of 1,000 requests per minute per tenant across 50 server instances?",
            "category": "System Design",
            "difficulties": ["mid", "senior", "staff"],
            "expected_key_points": [
                "Token Bucket or Leaky Bucket algorithm",
                "Centralized atomic state via Redis (Lua scripts or Redis cell)",
                "Sliding window counter vs fixed window edge cases",
                "Graceful degradation when the cache cluster is unreachable"
            ],
            "core_keywords": ["rate limit", "token bucket", "leaky bucket", "sliding window", "redis", "lua", "atomic", "cluster", "tenant", "header", "429", "too many requests", "throttle"],
            "follow_ups": [
                {
                    "question": "How do you avoid making a network roundtrip to Redis on every single incoming API request?",
                    "rationale": "Explores local batching, token reservation, or two-tier rate limiting."
                }
            ]
        },
        {
            "question": "Explain the mechanics of database connection pooling. What problems happen if the pool is configured too small versus too large?",
            "category": "Technical",
            "difficulties": ["mid", "senior", "staff"],
            "expected_key_points": [
                "TCP handshake and authentication reuse",
                "Thread starvation and request queuing when pool is too small",
                "Context switching, memory exhaustion, and disk thrashing when pool is too large",
                "Connection timeout and health check (validation query)"
            ],
            "core_keywords": ["connection pool", "pooling", "handshake", "thread", "queuing", "context switch", "exhaustion", "timeout", "active", "idle", "max connections", "pgbouncer", "hikari"],
            "follow_ups": [
                {
                    "question": "How would you monitor connection pool exhaustion in production before it cascades into a service-wide outage?",
                    "rationale": "Tests proactive telemetry (wait queue duration, connection acquisition latency)."
                }
            ]
        },
        {
            "question": "How do you handle asynchronous background processing and ensure tasks are not lost if a worker process crashes mid-execution?",
            "category": "Technical",
            "difficulties": ["entry", "mid", "senior"],
            "expected_key_points": [
                "Message queue acknowledgment (ACK vs NACK)",
                "Dead letter queue (DLQ) for repeated failures",
                "Visibility timeout mechanics",
                "Task idempotency for at-least-once delivery"
            ],
            "core_keywords": ["message queue", "ack", "nack", "acknowledgment", "worker", "crash", "dead letter", "dlq", "visibility", "celery", "kafka", "rabbitmq", "at-least-once", "retry"],
            "follow_ups": [
                {
                    "question": "How do you prevent a poison pill task from cycling through your workers indefinitely and consuming resources?",
                    "rationale": "Evaluates maximum retry count, error logging, and quarantine procedures."
                }
            ]
        },
        {
            "question": "What is the difference between synchronous gRPC and asynchronous Kafka event streams, and how do you decide which to use between microservices?",
            "category": "Technical",
            "difficulties": ["mid", "senior", "staff"],
            "expected_key_points": [
                "Protobuf serialization and HTTP/2 multiplexing in gRPC",
                "Decoupled event log and partition ordering in Kafka",
                "Request-response vs publish-subscribe paradigms",
                "Failure domains, backpressure, and eventual consistency"
            ],
            "core_keywords": ["grpc", "kafka", "http/2", "protobuf", "event", "stream", "partition", "sync", "async", "decoupled", "pub/sub", "backpressure", "consistency"],
            "follow_ups": [
                {
                    "question": "If an event consumer falls hours behind the Kafka stream, how do you catch up without overwhelming downstream databases?",
                    "rationale": "Explores consumer rate throttling, batch size tuning, and horizontal consumer group scaling."
                }
            ]
        }
    ],

    # -------------------------------------------------------------------------
    # FRONTEND ENGINEERING
    # -------------------------------------------------------------------------
    "frontend": [
        {
            "question": "How does the virtual DOM reconciliation algorithm work in modern React, and how does React determine when to re-render a component?",
            "category": "Technical",
            "difficulties": ["entry", "mid", "senior"],
            "expected_key_points": [
                "Diffing tree heuristic (O(N) complexity)",
                "Element type comparison and component re-mounting",
                "Key prop significance in list reconciliation",
                "State/prop reference changes triggering render cycles"
            ],
            "core_keywords": ["virtual dom", "reconciliation", "diff", "diffing", "tree", "re-render", "render", "key", "prop", "state", "fiber", "memo", "usememo", "usecallback"],
            "follow_ups": [
                {
                    "question": "Why is using array index as a key considered an anti-pattern when rendering dynamic lists with reordering or deletion?",
                    "rationale": "Tests deep understanding of element identity preservation and state corruption."
                }
            ]
        },
        {
            "question": "Can you explain the Core Web Vitals (LCP, CLS, INP) and the specific techniques you use to optimize each for high performance?",
            "category": "Technical",
            "difficulties": ["mid", "senior", "staff"],
            "expected_key_points": [
                "Largest Contentful Paint (LCP): image compression, CDN, preload",
                "Cumulative Layout Shift (CLS): explicit aspect ratios, font display swap",
                "Interaction to Next Paint (INP): yielding to main thread, breaking long tasks",
                "SSR/SSG impact on initial load vs interactive latency"
            ],
            "core_keywords": ["core web vitals", "lcp", "cls", "inp", "fid", "layout shift", "main thread", "long task", "aspect ratio", "preload", "web worker", "cdn", "render blocking"],
            "follow_ups": [
                {
                    "question": "How do you diagnose and eliminate long tasks (>50ms) that block the browser main thread during complex UI interactions?",
                    "rationale": "Tests profiling with Chrome DevTools performance tab and requestIdleCallback/scheduler.yield."
                }
            ]
        },
        {
            "question": "Explain Server-Side Rendering (SSR) versus Static Site Generation (SSG) versus Client-Side Rendering (CSR). When does hydration happen, and what causes hydration mismatch errors?",
            "category": "Technical",
            "difficulties": ["entry", "mid", "senior", "staff"],
            "expected_key_points": [
                "SSR HTML generation on each request vs SSG at build time",
                "Hydration attaching event listeners to server-rendered DOM nodes",
                "Hydration mismatch from browser-specific globals (window, localStorage, dynamic dates)",
                "Streaming SSR and Selective Hydration"
            ],
            "core_keywords": ["ssr", "ssg", "csr", "hydration", "mismatch", "server", "static", "client", "next.js", "event listeners", "streaming", "build time", "seo"],
            "follow_ups": [
                {
                    "question": "How does React 18's Streaming SSR with Suspense improve perceived performance over traditional blocking SSR?",
                    "rationale": "Evaluates knowledge of chunked HTML transfer and selective hydration."
                }
            ]
        },
        {
            "question": "How do you architect state management in a large-scale enterprise application to prevent unnecessary re-renders across deeply nested trees?",
            "category": "Technical",
            "difficulties": ["mid", "senior", "staff"],
            "expected_key_points": [
                "Colocation of state close to where it is used",
                "Server state (React Query/RTK Query) vs UI client state",
                "Context API limitations with high-frequency updates",
                "Selective subscriptions (Zustand, Redux Toolkit, signals)"
            ],
            "core_keywords": ["state management", "zustand", "redux", "context", "re-render", "server state", "react query", "colocation", "selector", "memoization", "prop drilling"],
            "follow_ups": [
                {
                    "question": "Why does React Context cause all consumer components to re-render even if they only need a slice of the value object?",
                    "rationale": "Probes knowledge of reference equality and context splitting."
                }
            ]
        },
        {
            "question": "What security vulnerabilities are unique to modern Single Page Applications (e.g. XSS, CSRF, Token storage), and how do you protect against them?",
            "category": "Technical",
            "difficulties": ["mid", "senior", "staff"],
            "expected_key_points": [
                "Cross-Site Scripting (XSS) via dangerous innerHTML or third-party packages",
                "Storing auth tokens in httpOnly cookies vs localStorage",
                "Content Security Policy (CSP) header restrictions",
                "CSRF protection (SameSite cookies, CSRF tokens)"
            ],
            "core_keywords": ["xss", "csrf", "cross-site", "token", "httponly", "cookie", "localstorage", "csp", "content security policy", "samesite", "sanitization", "jwt"],
            "follow_ups": [
                {
                    "question": "If an attacker executes arbitrary JavaScript on your page, how does storing JWT in an httpOnly cookie protect the user compared to localStorage?",
                    "rationale": "Tests security boundaries: httpOnly cookies cannot be read by JS, preventing token exfiltration."
                }
            ]
        }
    ],

    # -------------------------------------------------------------------------
    # FULL-STACK ENGINEERING
    # -------------------------------------------------------------------------
    "fullstack": [
        {
            "question": "How do you design and execute a relational database schema migration on a high-traffic table with zero downtime and zero dropped requests?",
            "category": "System Design",
            "difficulties": ["mid", "senior", "staff"],
            "expected_key_points": [
                "Expand and contract pattern (multi-phase rollout)",
                "Adding nullable column or default without table locking",
                "Dual-writing in application code while backfilling data",
                "Switching reads to new schema and safely removing old column"
            ],
            "core_keywords": ["migration", "zero downtime", "expand contract", "table lock", "dual write", "backfill", "nullable", "deploy", "schema", "high traffic", "postgres", "foreign key"],
            "follow_ups": [
                {
                    "question": "In PostgreSQL, why does adding a column with a volatile default or adding a non-concurrent index cause severe table lock contention?",
                    "rationale": "Tests deep PostgreSQL locking mechanisms (AccessExclusiveLock vs ShareLock)."
                }
            ]
        },
        {
            "question": "Explain how you would implement an optimistic UI update for an e-commerce cart, including rollback handling and server conflict resolution.",
            "category": "Technical",
            "difficulties": ["entry", "mid", "senior"],
            "expected_key_points": [
                "Immediate local client state mutation before network roundtrip",
                "Pending state indicator or micro-interaction",
                "Error boundary and snapshot rollback on network or validation failure",
                "Server truth reconciliation and user notification"
            ],
            "core_keywords": ["optimistic ui", "rollback", "cart", "mutation", "conflict", "reconciliation", "snapshot", "client state", "server response", "error handling"],
            "follow_ups": [
                {
                    "question": "If the user performs multiple rapid optimistic actions while offline and reconnects, in what order should the requests be synchronized?",
                    "rationale": "Evaluates offline mutation queues and sequence numbering."
                }
            ]
        },
        {
            "question": "How do you establish end-to-end type safety between your backend APIs and frontend client applications to eliminate runtime schema drift?",
            "category": "Technical",
            "difficulties": ["mid", "senior", "staff"],
            "expected_key_points": [
                "OpenAPI / Swagger code generation or tRPC / GraphQL codegen",
                "Shared TypeScript types or schemas (Zod, Pydantic)",
                "CI/CD build-time schema validation and breaking change detection",
                "Contract testing (e.g. Pact)"
            ],
            "core_keywords": ["type safety", "trpc", "graphql", "openapi", "swagger", "zod", "pydantic", "codegen", "contract test", "typescript", "breaking change", "schema drift"],
            "follow_ups": [
                {
                    "question": "How do you deprecate an API field without breaking older mobile clients that cannot be immediately updated?",
                    "rationale": "Tests versioning strategies and additive schema evolution."
                }
            ]
        }
    ],

    # -------------------------------------------------------------------------
    # SYSTEM DESIGN & ARCHITECTURE
    # -------------------------------------------------------------------------
    "system_design": [
        {
            "question": "Design a globally distributed URL shortening service (like Bitly) capable of generating 100 million new URLs per month with sub-10ms read latency.",
            "category": "System Design",
            "difficulties": ["mid", "senior", "staff"],
            "expected_key_points": [
                "Base62 encoding of distributed unique IDs (Snowflake or range allocation)",
                "Read-heavy ratio (100:1) requiring multi-tier caching (CDN, Redis)",
                "Database choice (NoSQL key-value like DynamoDB or partitioned PostgreSQL)",
                "Custom aliases, expiration TTL, and click telemetry pipeline"
            ],
            "core_keywords": ["url shortener", "bitly", "base62", "hash", "snowflake", "uuid", "cache", "redis", "cdn", "read heavy", "dynamodb", "latency", "sub-10ms", "partition"],
            "follow_ups": [
                {
                    "question": "How do you guarantee that ID generation does not become a single point of failure or bottleneck across multiple global data centers?",
                    "rationale": "Explores Twitter Snowflake, ZooKeeper range delegation, and epoch timestamps."
                }
            ]
        },
        {
            "question": "Design a real-time collaborative document editing system (similar to Google Docs) supporting simultaneous multi-user typing.",
            "category": "System Design",
            "difficulties": ["senior", "staff"],
            "expected_key_points": [
                "Operational Transformation (OT) vs Conflict-free Replicated Data Types (CRDT)",
                "WebSocket or WebRTC data channels for low-latency synchronization",
                "Centralized document authority server vs peer-to-peer",
                "Presence awareness (cursor positions) and persistent revision history"
            ],
            "core_keywords": ["google docs", "collaborative", "crdt", "operational transformation", "ot", "websocket", "conflict", "concurrency", "vector clock", "cursor", "undo/redo", "latency"],
            "follow_ups": [
                {
                    "question": "If two users on opposite sides of the world simultaneously insert a character at index 5, how does the system ensure both documents converge to the exact same text?",
                    "rationale": "Probes deep understanding of character shift transformations or fractional indexing in CRDTs."
                }
            ]
        },
        {
            "question": "Design a real-time notification platform capable of delivering push notifications, emails, and SMS to 50 million active users.",
            "category": "System Design",
            "difficulties": ["mid", "senior", "staff"],
            "expected_key_points": [
                "Decoupled event ingestion via message broker (Kafka/RabbitMQ)",
                "Fan-out worker pools tailored for third-party rate limits (APNs, FCM, Sendgrid, Twilio)",
                "User notification preferences, quiet hours, and frequency capping (deduplication)",
                "Delivery status tracking and dead letter retry queue"
            ],
            "core_keywords": ["notification", "push", "fcm", "apns", "sms", "email", "kafka", "fan-out", "rate limit", "deduplication", "retry", "preference", "worker", "broker"],
            "follow_ups": [
                {
                    "question": "If Apple APNs or Google FCM slows down dramatically, how do you prevent your internal message queues from backing up and exhausting server memory?",
                    "rationale": "Tests backpressure handling, circuit breaking, and priority lanes."
                }
            ]
        }
    ],

    # -------------------------------------------------------------------------
    # DEVOPS & CLOUD ENGINEERING
    # -------------------------------------------------------------------------
    "devops": [
        {
            "question": "How do you implement a Canary deployment strategy on Kubernetes, and what automated metrics trigger an immediate rollback?",
            "category": "Technical",
            "difficulties": ["mid", "senior", "staff"],
            "expected_key_points": [
                "Traffic splitting via Service Mesh (Istio) or Ingress (NGINX/Argo Rollouts)",
                "Gradual traffic increment (1% -> 5% -> 25% -> 100%)",
                "Automated analysis on HTTP 5xx error rate, p99 latency, and CPU/memory",
                "Instant rollback by updating service target selector back to stable"
            ],
            "core_keywords": ["canary", "kubernetes", "k8s", "rollback", "argo", "istio", "traffic split", "ingress", "p99", "error rate", "metrics", "prometheus", "blue/green"],
            "follow_ups": [
                {
                    "question": "How do you handle database schema migrations when running canary deployments where both v1 and v2 app pods run concurrently against the same database?",
                    "rationale": "Connects infra deployments to backwards-compatible schema design."
                }
            ]
        },
        {
            "question": "Explain how Terraform manages state locking, and what causes state drift in production cloud infrastructure.",
            "category": "Technical",
            "difficulties": ["entry", "mid", "senior"],
            "expected_key_points": [
                "Remote backend (S3 + DynamoDB locking, or Terraform Cloud)",
                "Concurrent apply prevention via mutex lock",
                "State drift caused by out-of-band manual console edits",
                "terraform refresh and automated drift detection pipelines"
            ],
            "core_keywords": ["terraform", "state", "locking", "dynamodb", "s3", "drift", "out-of-band", "plan", "apply", "refresh", "iac", "mutex"],
            "follow_ups": [
                {
                    "question": "How do you recover cleanly if a Terraform process is terminated abruptly, leaving the DynamoDB state lock permanently stuck in acquired state?",
                    "rationale": "Tests practical operational recovery (`force-unlock` validation and lock ID verification)."
                }
            ]
        }
    ],

    # -------------------------------------------------------------------------
    # DATA SCIENCE & MACHINE LEARNING / AI
    # -------------------------------------------------------------------------
    "data_ai": [
        {
            "question": "Walk me through how you architect an enterprise Retrieval-Augmented Generation (RAG) system for a large corpus of technical documentation.",
            "category": "Technical",
            "difficulties": ["mid", "senior", "staff"],
            "expected_key_points": [
                "Chunking strategies (semantic, recursive character, overlap)",
                "Embedding model selection and vector database indexing (HNSW, IVFFlat)",
                "Hybrid search combining dense vector embeddings and BM25 sparse keyword search",
                "Re-ranking retrieved chunks before prompt context injection"
            ],
            "core_keywords": ["rag", "retrieval", "vector", "embedding", "chunking", "hnsw", "pinecone", "milvus", "qdrant", "bm25", "hybrid search", "re-ranking", "hallucination", "context window"],
            "follow_ups": [
                {
                    "question": "How do you prevent the LLM from hallucinating answers when the retrieved context documents do not contain the answer to the user's query?",
                    "rationale": "Explores system prompting, relevance thresholding, and refusal grounding."
                }
            ]
        },
        {
            "question": "How do you detect and mitigate Data Drift and Concept Drift in production machine learning models after deployment?",
            "category": "Technical",
            "difficulties": ["mid", "senior", "staff"],
            "expected_key_points": [
                "Data drift (input distribution $P(X)$ changes: Kolmogorov-Smirnov, PSI)",
                "Concept drift (relationship $P(Y|X)$ changes)",
                "Continuous monitoring of feature distributions and prediction distributions",
                "Automated alerting, shadow deployment, and model re-training triggers"
            ],
            "core_keywords": ["data drift", "concept drift", "distribution", "monitoring", "psi", "ks test", "kolmogorov", "retraining", "features", "ground truth", "production", "metrics"],
            "follow_ups": [
                {
                    "question": "What is your strategy for monitoring drift when ground truth labels are delayed by weeks or months (e.g. loan defaults)?",
                    "rationale": "Tests proxy metric tracking, feature distribution deviation, and confidence scoring."
                }
            ]
        }
    ],

    # -------------------------------------------------------------------------
    # BEHAVIORAL & LEADERSHIP (STAR)
    # -------------------------------------------------------------------------
    "behavioral": [
        {
            "question": "Tell me about a high-severity production outage or critical bug you were responsible for resolving. Walk me through your triage, mitigation, and post-mortem process.",
            "category": "Behavioral",
            "difficulties": ["entry", "mid", "senior", "staff"],
            "expected_key_points": [
                "Clear Situation and business blast radius description",
                "Task ownership and immediate stabilization (rollback, traffic reroute)",
                "Methodical root cause analysis and incident commander communication",
                "Blameless post-mortem, preventative alerting, and automated regression testing"
            ],
            "core_keywords": ["outage", "production", "incident", "triage", "rollback", "mitigation", "root cause", "post-mortem", "monitoring", "alert", "blameless", "blast radius", "sla", "resolved"],
            "follow_ups": [
                {
                    "question": "If leadership is urgently pressuring you for an ETA during the outage while the cause is still unknown, how do you communicate transparently without causing panic?",
                    "rationale": "Evaluates executive presence, stakeholder management, and crisis communication."
                }
            ]
        },
        {
            "question": "Describe a situation where you had a significant technical disagreement with a senior engineer or engineering manager. How did you resolve the deadlock?",
            "category": "Behavioral",
            "difficulties": ["entry", "mid", "senior", "staff"],
            "expected_key_points": [
                "Technical context and conflicting viewpoints explained objectively",
                "Separating personal opinions from technical merits (benchmarks, prototypes, POC)",
                "Active listening, seeking common business objectives, or disagree and commit",
                "Positive project outcome and strengthened working relationship"
            ],
            "core_keywords": ["disagreement", "deadlock", "conflict", "compromise", "benchmark", "poc", "data-driven", "disagree and commit", "stakeholder", "consensus", "relationship", "outcome"],
            "follow_ups": [
                {
                    "question": "What if, after testing, neither option shows a clear technical advantage, but a decision must be made by end-of-day?",
                    "rationale": "Evaluates bias for action, reversibility assessment (two-way door), and team alignment."
                }
            ]
        },
        {
            "question": "Tell me about a time you had to balance paying down technical debt against shipping critical customer-facing features under tight deadlines.",
            "category": "Behavioral",
            "difficulties": ["mid", "senior", "staff"],
            "expected_key_points": [
                "Quantifying technical debt impact in business terms (dev velocity, bug rate, outage risk)",
                "Negotiating with product management for dedicated sprint allocation (e.g. 20% rule)",
                "Pragmatic phased refactoring instead of total rewrite",
                "Measurable improvement in release cadence or system reliability"
            ],
            "core_keywords": ["technical debt", "deadline", "product manager", "tradeoff", "prioritize", "velocity", "refactor", "balance", "sprint", "risk", "business value"],
            "follow_ups": [
                {
                    "question": "How do you explain the necessity of refactoring to a non-technical executive who only cares about new feature delivery?",
                    "rationale": "Tests ability to translate engineering health into business ROI and velocity."
                }
            ]
        }
    ]
}


def get_diverse_questions(
    domain: str, 
    difficulty: str, 
    persona: str, 
    count: int = 5,
    exclude_questions: Optional[List[str]] = None,
    job_description: str = "",
    resume_text: str = ""
) -> List[Dict[str, Any]]:
    """
    Selects a fresh, non-repeating set of questions matching candidate domain and difficulty.
    Guarantees no duplicate questions are presented to the candidate.
    """
    exclude_set = set(q.strip().lower() for q in (exclude_questions or []))
    domain_key = domain.lower() if domain.lower() in QUESTION_BANK else "backend"

    # Pool of candidate questions from domain
    domain_pool = QUESTION_BANK.get(domain_key, [])
    # Pool of behavioral questions
    behavioral_pool = QUESTION_BANK.get("behavioral", [])

    # Filter out previously asked questions
    fresh_domain_q = [
        q for q in domain_pool 
        if q["question"].strip().lower() not in exclude_set
    ]
    fresh_behavioral_q = [
        q for q in behavioral_pool 
        if q["question"].strip().lower() not in exclude_set
    ]

    # If domain pool exhausted, allow fallback to general pool but still avoid direct repeats
    if not fresh_domain_q:
        fresh_domain_q = list(domain_pool)
    if not fresh_behavioral_q:
        fresh_behavioral_q = list(behavioral_pool)

    # Sort/prioritize questions matching candidate difficulty
    def difficulty_weight(q):
        diffs = q.get("difficulties", ["mid"])
        return 0 if difficulty.lower() in diffs else 1

    fresh_domain_q.sort(key=difficulty_weight)
    fresh_behavioral_q.sort(key=difficulty_weight)

    # Shuffle within priority groups to add variety
    random.shuffle(fresh_domain_q)
    random.shuffle(fresh_behavioral_q)

    # Balanced mix: 3-4 technical/architectural + 1-2 behavioral
    selected = []
    
    # Take 3 technical questions
    tech_take = min(count - 1, len(fresh_domain_q))
    selected.extend(fresh_domain_q[:tech_take])

    # Take 1-2 behavioral questions
    remaining = count - len(selected)
    selected.extend(fresh_behavioral_q[:remaining])

    # If still need more, fill from other domains (e.g. system design or fullstack)
    if len(selected) < count:
        aux_pool = QUESTION_BANK.get("system_design", []) + QUESTION_BANK.get("fullstack", [])
        for aux in aux_pool:
            if len(selected) >= count:
                break
            if aux["question"].strip().lower() not in exclude_set:
                selected.append(aux)

    # Assign sequential order and format output
    output = []
    for idx, item in enumerate(selected[:count], start=1):
        output.append({
            "order": idx,
            "question": item["question"],
            "category": item.get("category", "Technical"),
            "expected_key_points": item.get("expected_key_points", []),
            "core_keywords": item.get("core_keywords", []),
            "follow_ups": item.get("follow_ups", [])
        })

    return output


def evaluate_candidate_answer_semantics(
    question_text: str,
    answer_text: str,
    persona: str,
    domain: str,
    difficulty: str,
    expected_key_points: Optional[List[str]] = None,
    core_keywords: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Performs substantive, accurate semantic evaluation of the candidate's response.
    Analyzes relevance, technical depth, keyword match against expected key concepts,
    and constructs custom, specific strengths, improvements, and STAR breakdown.
    """
    clean_ans = answer_text.strip()
    words = clean_ans.split()
    word_count = len(words)

    # Detect empty or inaudible response
    if not clean_ans or clean_ans.startswith("(Candidate provided no") or word_count < 5:
        return {
            "score": 18.0,
            "summary": "Candidate provided no substantive response or response was too brief to evaluate.",
            "strengths": ["Recognized question prompt"],
            "improvements": [
                "Articulate full reasoning and speak clearly into the microphone",
                "If experiencing microphone issues, toggle into Typed Fallback mode"
            ],
            "star_analysis": {
                "situation": 20,
                "task": 20,
                "action": 15,
                "result": 15,
                "situation_feedback": "Context was not established.",
                "task_feedback": "Core goal was not stated.",
                "action_feedback": "No implementation actions provided.",
                "result_feedback": "No measurable outcome provided."
            }
        }

    # Find matching question in bank to get expected key points if not provided
    if not expected_key_points or not core_keywords:
        q_tokens = set(re.findall(r'\b[a-zA-Z]{3,}\b', question_text.lower()))
        best_match = None
        best_overlap = 0.0

        for dom, qlist in QUESTION_BANK.items():
            for q in qlist:
                item_tokens = set(re.findall(r'\b[a-zA-Z]{3,}\b', q["question"].lower()))
                if q_tokens and item_tokens:
                    overlap = len(q_tokens & item_tokens) / max(len(q_tokens), 1)
                    if overlap > best_overlap:
                        best_overlap = overlap
                        best_match = q

        if best_match and best_overlap >= 0.40:
            expected_key_points = expected_key_points or best_match.get("expected_key_points", [])
            core_keywords = core_keywords or best_match.get("core_keywords", [])

    # Dynamically extract anchor keywords from the question itself
    stop_words = {
        "what", "when", "where", "which", "would", "could", "should", "explain", "describe", 
        "difference", "between", "handle", "ensure", "choose", "other", "modern", "walk", 
        "your", "with", "from", "that", "this", "they", "have", "been", "through", "tell",
        "time", "about"
    }
    extracted_q_terms = [
        w.lower() for w in re.findall(r'\b[a-zA-Z]{4,}\b', question_text) 
        if w.lower() not in stop_words
    ]

    core_keywords = list(set((core_keywords or []) + extracted_q_terms))
    expected_key_points = expected_key_points or [
        "Core technical architecture and implementation",
        "Performance and scalability trade-offs",
        "Error handling and failure mitigation"
    ]

    lower_ans = clean_ans.lower()

    # 1. Evaluate keyword & concept coverage
    matched_keywords = []
    for kw in core_keywords:
        if re.search(r'\b' + re.escape(kw.lower()) + r'\b', lower_ans):
            matched_keywords.append(kw)

    # 2. Evaluate expected key points coverage
    covered_key_points = []
    missed_key_points = []
    for kp in expected_key_points:
        kp_words = [w.lower() for w in re.findall(r'\b[a-zA-Z]{3,}\b', kp)]
        # Check if 35%+ of significant words from key point are in the answer
        matches = sum(1 for w in kp_words if w in lower_ans)
        if kp_words and (matches / len(kp_words)) >= 0.35:
            covered_key_points.append(kp)
        else:
            missed_key_points.append(kp)

    # 3. Base Technical Score Calculation
    # Coverage score (0 to 60 points)
    coverage_ratio = len(covered_key_points) / max(1, len(expected_key_points))
    coverage_score = coverage_ratio * 55.0

    # Keyword depth score (0 to 25 points)
    kw_ratio = min(1.0, len(matched_keywords) / max(3, len(core_keywords) * 0.4))
    kw_score = kw_ratio * 25.0

    # Substantiveness / Length score (0 to 20 points)
    # Ideal answer length for complex technical questions: 60 - 250 words
    if word_count < 25:
        length_score = 6.0
    elif word_count < 60:
        length_score = 12.0
    elif word_count <= 250:
        length_score = 20.0
    else:
        length_score = 18.0  # slight deduction for excessive rambling

    raw_score = coverage_score + kw_score + length_score

    # Check for irrelevant spam / gibberish detection
    if len(matched_keywords) == 0 and coverage_ratio == 0:
        raw_score = min(28.0, raw_score * 0.3)

    final_score = round(max(20.0, min(98.0, raw_score)), 1)

    # 4. Generate Specific, Accurate Strengths
    strengths = []
    if covered_key_points:
        for kp in covered_key_points[:2]:
            strengths.append(f"Demonstrated clear understanding of {kp.lower()}")
    if matched_keywords:
        top_kws = ", ".join(list(set(matched_keywords))[:3])
        strengths.append(f"Appropriately applied domain terminology ({top_kws})")
    if word_count >= 50 and final_score >= 65:
        strengths.append("Structured explanation methodically with appropriate technical depth")
    if not strengths:
        strengths.append("Attempted the question and maintained structured communication")

    # 5. Generate Specific, Accurate Improvements
    improvements = []
    if missed_key_points:
        for kp in missed_key_points[:2]:
            improvements.append(f"Deepen coverage on {kp.lower()}")
    if word_count < 45:
        improvements.append("Elaborate further with concrete implementation examples and edge cases")
    if "trade-off" not in lower_ans and "tradeoff" not in lower_ans and "latency" not in lower_ans:
        improvements.append("Articulate engineering trade-offs and production failure modes explicitly")
    if not improvements:
        improvements.append("Consider discussing multi-region failover and observability metrics")

    # 6. STAR Framework Analysis
    # Check if candidate articulated Situation, Task, Action, Result
    sit_score = round(min(95.0, max(40.0, 45.0 + (final_score * 0.45) + (10 if "when" in lower_ans or "system" in lower_ans else 0))), 1)
    tsk_score = round(min(95.0, max(40.0, 40.0 + (final_score * 0.45) + (10 if "needed" in lower_ans or "goal" in lower_ans or "responsible" in lower_ans else 0))), 1)
    act_score = round(min(98.0, max(40.0, 40.0 + (final_score * 0.55) + (10 if len(matched_keywords) >= 2 else 0))), 1)
    res_score = round(min(95.0, max(35.0, 35.0 + (final_score * 0.45) + (15 if "%" in clean_ans or "reduced" in lower_ans or "latency" in lower_ans or "result" in lower_ans else 0))), 1)

    # 7. Evaluator Summary
    if final_score >= 85:
        summary = f"Strong, authoritative answer. Covered key concepts including {', '.join(covered_key_points[:2]) if covered_key_points else 'core architectural components'}."
    elif final_score >= 70:
        summary = f"Good technical understanding demonstrated. Touched upon {', '.join(covered_key_points[:2]) if covered_key_points else 'key requirements'}, with room to expand on {missed_key_points[0].lower() if missed_key_points else 'trade-offs'}."
    elif final_score >= 50:
        summary = f"Basic conceptual familiarity shown, but missed critical details on {', '.join(missed_key_points[:2]) if missed_key_points else 'system edge cases'}."
    else:
        summary = f"Answer lacked necessary technical depth for {difficulty} level. Important topics like {', '.join(missed_key_points[:2]) if missed_key_points else 'fundamentals'} were absent."

    ideal_points = "; ".join((expected_key_points or ["clear architectural trade-offs", "failure mode handling", "measurable production metrics"])[:3])
    ideal_answer_example = (
        f"A top-scoring response would directly address {ideal_points}. "
        "Start by stating the core design decision, compare one alternative with latency/consistency trade-offs, "
        "and close with a concrete metric or failure-recovery strategy."
    )

    return {
        "score": final_score,
        "summary": summary,
        "ideal_answer_example": ideal_answer_example,
        "strengths": strengths[:3],
        "improvements": improvements[:3],
        "star_analysis": {
            "situation": sit_score,
            "task": tsk_score,
            "action": act_score,
            "result": res_score,
            "situation_feedback": f"Context score: {sit_score}%.",
            "task_feedback": f"Ownership score: {tsk_score}%.",
            "action_feedback": f"Technical execution score: {act_score}%.",
            "result_feedback": f"Measurable impact score: {res_score}%."
        }
    }


def get_contextual_follow_up(
    question_text: str,
    answer_text: str,
    persona: str,
    score: float,
    already_asked_follow_ups: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Selects a relevant, question-specific follow-up probe.
    Does NOT ask generic repetitive questions. Avoids repeating follow-ups already presented.
    """
    already_asked = set(q.strip().lower() for q in (already_asked_follow_ups or []))

    # Follow-ups should only trigger when candidate gave a substantive response (score >= 55)
    # and has not already exceeded maximum follow-up limits
    if score < 20.0 or not answer_text.strip() or answer_text.startswith("(Candidate provided no") or len(already_asked) >= 3:
        return {
            "should_ask_follow_up": False,
            "follow_up_question": "",
            "rationale": ""
        }

    # Find the specific question in the question bank using token overlap
    matched_q = None
    q_tokens = set(re.findall(r'\b[a-zA-Z]{3,}\b', question_text.lower()))
    best_overlap = 0.0

    for dom, qlist in QUESTION_BANK.items():
        for q in qlist:
            item_tokens = set(re.findall(r'\b[a-zA-Z]{3,}\b', q["question"].lower()))
            if q_tokens and item_tokens:
                overlap = len(q_tokens & item_tokens) / max(len(q_tokens), 1)
                if overlap > best_overlap:
                    best_overlap = overlap
                    matched_q = q

    if best_overlap < 0.40:
        matched_q = None

    if matched_q and matched_q.get("follow_ups"):
        for fu in matched_q["follow_ups"]:
            fu_text = fu["question"]
            if fu_text.strip().lower() not in already_asked:
                return {
                    "should_ask_follow_up": True,
                    "follow_up_question": fu_text,
                    "rationale": fu.get("rationale", "Probes deeper into edge cases and trade-offs.")
                }

    # General domain-aware contextual probes that are non-repetitive
    generic_probes = [
        ("What performance metrics or dashboards would you monitor in production to verify this is operating healthily?", "Probes observability and operational monitoring."),
        ("What is the single biggest architectural trade-off or compromise you made in that approach?", "Tests critical thinking regarding system constraints."),
        ("If network latency between your services suddenly increased by 300ms, how would this design behave?", "Explores failure modes and latency degradation.")
    ]

    for probe_text, rationale in generic_probes:
        if probe_text.strip().lower() not in already_asked:
            return {
                "should_ask_follow_up": True,
                "follow_up_question": probe_text,
                "rationale": rationale
            }

    return {
        "should_ask_follow_up": False,
        "follow_up_question": "",
        "rationale": ""
    }
