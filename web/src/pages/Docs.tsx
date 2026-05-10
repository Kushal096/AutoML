import { useState } from "react";
import Layout from "@/components/Layout";
import { 
  Book, 
  Code, 
  Download, 
  Zap, 
  Database, 
  TrendingUp, 
  Activity,
  Copy,
  CheckCircle2,
  ChevronRight
} from "lucide-react";

interface CodeBlockProps {
  code: string;
  language?: string;
}

function CodeBlock({ code, language = "python" }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const copyToClipboard = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative group">
      <pre className="bg-bg-secondary border-2 border-border rounded-lg p-4 overflow-x-auto">
        <code className={`text-sm text-text-primary font-mono`}>{code}</code>
      </pre>
      <button
        onClick={copyToClipboard}
        className="absolute top-3 right-3 p-2 bg-bg-primary/80 hover:bg-bg-primary border-2 border-border rounded-lg transition-colors opacity-0 group-hover:opacity-100"
        title="Copy code"
      >
        {copied ? (
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
        ) : (
          <Copy className="w-4 h-4 text-text-muted" />
        )}
      </button>
    </div>
  );
}

export default function Docs() {
  const [activeSection, setActiveSection] = useState<string | null>(null);

  const toggleSection = (section: string) => {
    setActiveSection(activeSection === section ? null : section);
  };

  const installationCode = `pip install mlops-sdk

# Or install from source
cd sdk
pip install -e .`;

  const quickStartCode = `from mlops_sdk import MLOpsClient
import pandas as pd

# Initialize client
client = MLOpsClient(base_url="http://localhost:8000")

# Login
client.login(email="user@example.com", password="password")

# Create a project (system will be auto-detected by LLM)
project = client.create_project(
    name="My Recommendation System"
)
project_id = project["id"]

# Upload data
data = pd.DataFrame({
    "user_id": [1, 2, 3],
    "item_id": [10, 20, 30],
    "rating": [5, 4, 3]
})
client.upload_data(project_id, data)

# Train model (automatic after upload)
# Make predictions
predictions = client.predict(
    project_id=project_id,
    user_id="user_123",
    top_k=10
)
print(predictions)`;

  const authCode = `# Signup
client.signup(name="John Doe", email="john@example.com", password="secure123")

# Login
client.login(email="john@example.com", password="secure123")

# Refresh API key
client.refresh_api_key()`;

  const projectsCode = `# Create project (system auto-detected by LLM)
project = client.create_project(name="My Project")

# List projects
projects = client.list_projects()

# Get project
project = client.get_project(project_id)

# Delete project
client.delete_project(project_id)`;

  const dataUploadCode = `# Upload DataFrame
client.upload_data(project_id, df)

# Upload from file
client.upload_data(project_id, "data.csv")

# Upload with context for LLM analysis
client.upload_data(
    project_id, 
    df,
    context="This is a movie recommendation dataset"
)`;

  const trainingCode = `# Training is automatic after dataset upload
# But you can also manually trigger it
result = client.train(project_id)

# Get training status
status = client.get_training_status(project_id)

# Get models
models = client.get_models(project_id)`;

  const predictionsCode = `# Single prediction (Recommendation)
pred = client.predict(
    project_id=project_id, 
    user_id="u123", 
    top_k=10
)

# Single prediction (Churn)
pred = client.predict(
    project_id=project_id,
    customer_id="c123",
    input_data={"age": 35, "usage": 150}
)

# Batch predictions
preds = client.predict_batch(
    project_id=project_id,
    users=["u1", "u2", "u3"],
    top_k=5
)`;

  const monitoringCode = `# Get metrics
metrics = client.get_metrics(project_id)

# Get drift status
drift = client.get_drift_status(project_id, days=7)

# Detect drift in new data
drift = client.detect_drift(project_id, {"feature1": 123})

# Get dashboard
dashboard = client.get_dashboard(project_id)

# Get alerts
alerts = client.get_alerts(project_id)`;

  const errorHandlingCode = `from mlops_sdk import MLOpsClient, AuthenticationError, APIError

try:
    client = MLOpsClient()
    client.login(email="wrong@email.com", password="wrong")
except AuthenticationError as e:
    print(f"Auth failed: {e}")
except APIError as e:
    print(f"API error: {e.status_code} - {e}")`;

  const sections = [
    {
      id: "installation",
      title: "Installation",
      icon: Download,
      content: (
        <div className="space-y-4">
          <p className="text-text-primary">
            Install the MLOps SDK using pip:
          </p>
          <CodeBlock code={installationCode} />
        </div>
      ),
    },
    {
      id: "quickstart",
      title: "Quick Start",
      icon: Zap,
      content: (
        <div className="space-y-4">
          <p className="text-text-primary">
            Get started with the SDK in just a few lines of code. The system uses AI to automatically detect your ML system type from your data.
          </p>
          <CodeBlock code={quickStartCode} />
        </div>
      ),
    },
    {
      id: "authentication",
      title: "Authentication",
      icon: Database,
      content: (
        <div className="space-y-4">
          <p className="text-text-primary">
            Authenticate with the platform using email and password, or use an API key.
          </p>
          <CodeBlock code={authCode} />
        </div>
      ),
    },
    {
      id: "projects",
      title: "Projects",
      icon: Database,
      content: (
        <div className="space-y-4">
          <p className="text-text-primary">
            Create and manage ML projects. The system type is automatically detected by the LLM when you upload your dataset.
          </p>
          <CodeBlock code={projectsCode} />
        </div>
      ),
    },
    {
      id: "data",
      title: "Data Upload",
      icon: Database,
      content: (
        <div className="space-y-4">
          <p className="text-text-primary">
            Upload your datasets as DataFrames or CSV files. Provide context to help the LLM understand your data better.
          </p>
          <CodeBlock code={dataUploadCode} />
        </div>
      ),
    },
    {
      id: "training",
      title: "Training",
      icon: TrendingUp,
      content: (
        <div className="space-y-4">
          <p className="text-text-primary">
            Models are automatically trained after dataset upload. You can also manually trigger training or check training status.
          </p>
          <CodeBlock code={trainingCode} />
        </div>
      ),
    },
    {
      id: "predictions",
      title: "Predictions",
      icon: Activity,
      content: (
        <div className="space-y-4">
          <p className="text-text-primary">
            Make predictions using your trained models. Supports single and batch predictions for different system types.
          </p>
          <CodeBlock code={predictionsCode} />
        </div>
      ),
    },
    {
      id: "monitoring",
      title: "Monitoring",
      icon: Activity,
      content: (
        <div className="space-y-4">
          <p className="text-text-primary">
            Monitor your models, track drift, and get alerts about model performance.
          </p>
          <CodeBlock code={monitoringCode} />
        </div>
      ),
    },
    {
      id: "errors",
      title: "Error Handling",
      icon: Code,
      content: (
        <div className="space-y-4">
          <p className="text-text-primary">
            Handle errors gracefully using the SDK's exception classes.
          </p>
          <CodeBlock code={errorHandlingCode} />
        </div>
      ),
    },
  ];

  return (
    <Layout>
      <div className="p-8 max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 rounded-xl bg-blue-500/20 border-2 border-blue-500/40 flex items-center justify-center">
              <Book className="w-6 h-6 text-blue-400" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-text-primary">SDK Documentation</h1>
              <p className="text-text-muted mt-1">Python SDK for the MLOps Platform</p>
            </div>
          </div>
        </div>

        {/* Introduction */}
        <div className="card border-2 border-border bg-bg-secondary p-6 mb-8">
          <h2 className="text-xl font-bold text-text-primary mb-3">About the SDK</h2>
          <p className="text-text-primary leading-relaxed">
            The MLOps SDK provides a simple Python interface to interact with the platform. 
            It features AI-powered system detection, automatic model training, and comprehensive monitoring capabilities.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <span className="px-3 py-1 bg-blue-500/10 text-blue-400 rounded-full text-xs font-semibold border border-blue-500/30">
              AI-Powered
            </span>
            <span className="px-3 py-1 bg-emerald-500/10 text-emerald-400 rounded-full text-xs font-semibold border border-emerald-500/30">
              Auto Training
            </span>
            <span className="px-3 py-1 bg-purple-500/10 text-purple-400 rounded-full text-xs font-semibold border border-purple-500/30">
              Easy to Use
            </span>
          </div>
        </div>

        {/* Documentation Sections */}
        <div className="space-y-4">
          {sections.map((section) => {
            const Icon = section.icon;
            const isActive = activeSection === section.id;

            return (
              <div
                key={section.id}
                className="card border-2 border-border bg-bg-secondary overflow-hidden"
              >
                <button
                  onClick={() => toggleSection(section.id)}
                  className="w-full flex items-center justify-between p-6 hover:bg-bg-primary/50 transition-colors"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-lg bg-primary/20 border-2 border-primary/40 flex items-center justify-center">
                      <Icon className="w-5 h-5 text-primary" />
                    </div>
                    <h2 className="text-lg font-bold text-text-primary">
                      {section.title}
                    </h2>
                  </div>
                  <ChevronRight
                    className={`w-5 h-5 text-text-muted transition-transform ${
                      isActive ? "rotate-90" : ""
                    }`}
                  />
                </button>
                {isActive && (
                  <div className="px-6 pb-6 border-t-2 border-border pt-6">
                    {section.content}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div className="mt-12 pt-8 border-t-2 border-border text-center">
          <p className="text-text-muted text-sm">
            Need help? Check the{" "}
            <a
              href="https://github.com/example/mlops-sdk"
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary hover:underline"
            >
              GitHub repository
            </a>{" "}
            or contact support.
          </p>
          <p className="text-text-muted text-xs mt-2">MIT License</p>
        </div>
      </div>
    </Layout>
  );
}

