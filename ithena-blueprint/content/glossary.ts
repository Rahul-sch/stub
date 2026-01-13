export interface GlossaryEntry {
  term: string;
  definition: string;
  seeAlso?: string[];
}

export const glossaryData: Record<string, GlossaryEntry> = {
  'Exactly-Once Semantics': {
    term: 'Exactly-Once Semantics',
    definition:
      'A delivery guarantee that ensures each message is processed exactly one time, even in the face of failures. Achieved by coordinating Kafka offset commits with database transactions - only committing the offset after successful database insert.',
    seeAlso: ['Kafka Consumer', 'Idempotence', 'Transaction'],
  },
  'Kafka Consumer': {
    term: 'Kafka Consumer',
    definition:
      'A client application that reads messages from Kafka topics. Consumers poll for messages in batches and track their position (offset) in each topic partition. Multiple consumers can form a consumer group for parallel processing.',
    seeAlso: ['Kafka Topic', 'Offset', 'Consumer Group'],
  },
  'Kafka Topic': {
    term: 'Kafka Topic',
    definition:
      'A named stream of records in Kafka. Topics are divided into partitions for scalability and parallelism. Producers write to topics, consumers read from topics.',
    seeAlso: ['Partition', 'Kafka Broker'],
  },
  'Offset': {
    term: 'Offset',
    definition:
      'A sequential ID number assigned to each message within a Kafka partition. Consumers use offsets to track which messages they have processed. Committing an offset tells Kafka "I have successfully processed all messages up to this point".',
    seeAlso: ['Kafka Consumer', 'Partition'],
  },
  'Partition': {
    term: 'Partition',
    definition:
      'A division of a Kafka topic for scalability and parallelism. Each partition is an ordered, immutable sequence of records. Messages with the same key always go to the same partition, preserving order.',
    seeAlso: ['Kafka Topic', 'Consumer Group'],
  },
  'Consumer Group': {
    term: 'Consumer Group',
    definition:
      'A set of Kafka consumers that cooperate to consume messages from a topic. Each partition is consumed by exactly one consumer in the group, enabling parallel processing while maintaining order per partition.',
    seeAlso: ['Kafka Consumer', 'Partition'],
  },
  'Kafka Broker': {
    term: 'Kafka Broker',
    definition:
      'A Kafka server that stores and serves messages. A Kafka cluster consists of multiple brokers for fault tolerance and scalability. Each broker handles read/write requests and replicates data.',
    seeAlso: ['Kafka Topic', 'Replication'],
  },
  'Exponential Backoff': {
    term: 'Exponential Backoff',
    definition:
      'A retry strategy where wait time doubles after each failed attempt (1s, 2s, 4s, 8s, etc.) up to a maximum. Prevents overwhelming a failing service while still recovering quickly from brief outages.',
    seeAlso: ['Retry Logic', 'Circuit Breaker'],
  },
  'Isolation Forest': {
    term: 'Isolation Forest',
    definition:
      'An unsupervised machine learning algorithm for anomaly detection. Works by randomly partitioning data - anomalies require fewer partitions to isolate than normal points. Fast and effective for high-dimensional data.',
    seeAlso: ['Anomaly Detection', 'LSTM Autoencoder'],
  },
  'LSTM Autoencoder': {
    term: 'LSTM Autoencoder',
    definition:
      'A neural network that learns to reconstruct normal time-series patterns using Long Short-Term Memory layers. Anomalies are detected when reconstruction error exceeds a threshold. Captures temporal dependencies that Isolation Forest misses.',
    seeAlso: ['Isolation Forest', 'Anomaly Detection', 'Time Series'],
  },
  'Anomaly Detection': {
    term: 'Anomaly Detection',
    definition:
      'The process of identifying data points that deviate significantly from expected patterns. Can use rule-based methods (threshold checks) or machine learning (Isolation Forest, LSTM). Critical for predictive maintenance in IoT.',
    seeAlso: ['Isolation Forest', 'LSTM Autoencoder'],
  },
  'JSONB': {
    term: 'JSONB',
    definition:
      'PostgreSQL\'s binary JSON storage format. Supports efficient indexing and querying of JSON data. Used in Ithena for custom_sensors column to store user-defined sensor data without schema changes.',
    seeAlso: ['PostgreSQL', 'Custom Sensors'],
  },
  'WebSocket': {
    term: 'WebSocket',
    definition:
      'A protocol providing full-duplex communication over a single TCP connection. Enables real-time bidirectional data flow between client and server. Used in Ithena for live sensor updates to the dashboard.',
    seeAlso: ['SocketIO', 'Real-Time'],
  },
  'SocketIO': {
    term: 'SocketIO',
    definition:
      'A library that enables real-time, bidirectional communication between web clients and servers using WebSocket (with fallbacks). Provides rooms, namespaces, and automatic reconnection.',
    seeAlso: ['WebSocket', 'Real-Time'],
  },
  'Graceful Shutdown': {
    term: 'Graceful Shutdown',
    definition:
      'A shutdown process that completes in-flight work before terminating. For Kafka consumers: finish processing current message, commit offset, close connections. Prevents data loss and duplicate processing.',
    seeAlso: ['Signal Handler', 'Kafka Consumer'],
  },
  'Signal Handler': {
    term: 'Signal Handler',
    definition:
      'Code that intercepts OS signals (SIGINT, SIGTERM) to enable graceful shutdown. Sets a flag (should_shutdown) that the main loop checks, rather than abruptly terminating.',
    seeAlso: ['Graceful Shutdown'],
  },
  'Idempotence': {
    term: 'Idempotence',
    definition:
      'The property that an operation can be applied multiple times without changing the result beyond the first application. Critical for exactly-once semantics - if a message is reprocessed, it shouldn\'t create duplicate data.',
    seeAlso: ['Exactly-Once Semantics', 'Transaction'],
  },
  'Transaction': {
    term: 'Transaction',
    definition:
      'A sequence of database operations that are executed as a single unit - all succeed or all fail (atomicity). In Ithena, database insert and Kafka offset commit are coordinated in a transaction for exactly-once semantics.',
    seeAlso: ['Exactly-Once Semantics', 'ACID'],
  },
  'ACID': {
    term: 'ACID',
    definition:
      'Atomicity, Consistency, Isolation, Durability - properties that guarantee database transactions are processed reliably. PostgreSQL is ACID-compliant, ensuring data integrity even during failures.',
    seeAlso: ['Transaction', 'PostgreSQL'],
  },
  'PostgreSQL': {
    term: 'PostgreSQL',
    definition:
      'An open-source, ACID-compliant relational database. Supports advanced features like JSONB, full-text search, and geospatial data. Ithena uses PostgreSQL (via Neon cloud) for sensor data persistence.',
    seeAlso: ['JSONB', 'ACID', 'Neon'],
  },
  'Neon': {
    term: 'Neon',
    definition:
      'A serverless PostgreSQL platform that separates compute and storage. Features instant branching, auto-scaling, and scale-to-zero. Ithena uses Neon for cost-effective, scalable database hosting.',
    seeAlso: ['PostgreSQL'],
  },
  'Time Series': {
    term: 'Time Series',
    definition:
      'Data points indexed in time order. Sensor readings are time-series data - each reading has a timestamp and sensor values. Patterns like seasonality and trends are important for anomaly detection.',
    seeAlso: ['LSTM Autoencoder', 'Sensor Data'],
  },
  'Sensor Data': {
    term: 'Sensor Data',
    definition:
      'Measurements from physical sensors monitoring equipment. Ithena tracks 50 sensor parameters (temperature, pressure, humidity, vibration, RPM, etc.) across industrial machines.',
    seeAlso: ['Time Series', 'IoT'],
  },
  'IoT': {
    term: 'IoT',
    definition:
      'Internet of Things - network of physical devices with sensors, software, and connectivity. Ithena is an IoT platform for industrial equipment monitoring and predictive maintenance.',
    seeAlso: ['Sensor Data', 'Edge Computing'],
  },
  'Custom Sensors': {
    term: 'Custom Sensors',
    definition:
      'User-defined sensors added at runtime via the dashboard. Stored in a JSONB column rather than fixed schema columns. Enables flexibility without database migrations.',
    seeAlso: ['JSONB', 'Sensor Data'],
  },
  'Hybrid Detection': {
    term: 'Hybrid Detection',
    definition:
      'Combining multiple anomaly detection methods (rule-based + Isolation Forest + LSTM) to leverage strengths of each. Rule-based catches obvious violations, IF catches statistical outliers, LSTM catches temporal anomalies.',
    seeAlso: ['Isolation Forest', 'LSTM Autoencoder', 'Anomaly Detection'],
  },
  'Replication': {
    term: 'Replication',
    definition:
      'Copying data across multiple servers for fault tolerance. Kafka replicates topic partitions across brokers. If one broker fails, another can serve the data.',
    seeAlso: ['Kafka Broker', 'Fault Tolerance'],
  },
  'Fault Tolerance': {
    term: 'Fault Tolerance',
    definition:
      'The ability of a system to continue operating correctly even when components fail. Achieved through replication, retries, graceful degradation, and redundancy.',
    seeAlso: ['Replication', 'Exponential Backoff'],
  },
};
