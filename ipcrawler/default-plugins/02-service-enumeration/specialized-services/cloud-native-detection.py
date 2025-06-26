from ipcrawler.plugins import ServiceScan

class CloudNativeDetection(ServiceScan):

	def __init__(self):
		super().__init__()
		self.name = "Cloud-Native & Container Detection"
		self.slug = 'cloud-native-detection'
		self.description = "Detects cloud-native technologies, containers, orchestration platforms, and modern infrastructure"
		self.priority = 0
		self.tags = ['default', 'safe', 'cloud', 'containers', 'modern']

	def configure(self):
		# Match all HTTP services for comprehensive coverage
		self.match_service_name('^http')
		self.match_service_name('^nacn_http$', negative_match=True)
		
		# === CONTAINER TECHNOLOGIES ===
		
		# Docker Detection
		self.add_pattern(r'(?i)docker[/-](\d+\.\d+\.\d+)', description='Docker Engine v{match1} detected - containerization platform')
		self.add_pattern(r'(?i)docker\.sock|/var/run/docker\.sock', description='CRITICAL: Docker socket exposed - container escape/privilege escalation risk')
		self.add_pattern(r'(?i)docker-compose|docker\.compose', description='Docker Compose detected - multi-container application orchestration')
		self.add_pattern(r'(?i)dockerfile|\.dockerignore', description='Docker build files detected - review for secrets and misconfigurations')
		self.add_pattern(r'(?i)/proc/1/cgroup.*docker|/.dockerenv', description='Running inside Docker container - check for escape vectors')
		self.add_pattern(r'(?i)docker.*registry|registry.*docker', description='Docker Registry detected - check for unauthenticated access')
		self.add_pattern(r'(?i)portainer|portainer-ce', description='Portainer Docker management interface detected - check default credentials')
		
		# Container Runtimes
		self.add_pattern(r'(?i)containerd|containerd\.sock', description='containerd runtime detected - container management')
		self.add_pattern(r'(?i)crio|cri-o', description='CRI-O container runtime detected - Kubernetes-focused runtime')
		self.add_pattern(r'(?i)podman|podman\.sock', description='Podman container runtime detected - daemonless container engine')
		self.add_pattern(r'(?i)runc|runC', description='runC container runtime detected - low-level container runtime')
		
		# === KUBERNETES & ORCHESTRATION ===
		
		# Kubernetes Core Components
		self.add_pattern(r'(?i)kubernetes[/-]v(\d+\.\d+\.\d+)', description='Kubernetes v{match1} detected - container orchestration platform')
		self.add_pattern(r'(?i)kube-apiserver|k8s.*apiserver', description='Kubernetes API Server detected - cluster control plane')
		self.add_pattern(r'(?i)kube-scheduler|k8s.*scheduler', description='Kubernetes Scheduler detected - pod scheduling component')
		self.add_pattern(r'(?i)kube-controller|k8s.*controller', description='Kubernetes Controller Manager detected - cluster state management')
		self.add_pattern(r'(?i)kubelet|k8s.*kubelet', description='Kubelet detected - node agent for pod management')
		self.add_pattern(r'(?i)kube-proxy|k8s.*proxy', description='Kube-proxy detected - network proxy service')
		self.add_pattern(r'(?i)etcd|etcd-cluster', description='etcd detected - Kubernetes cluster data store')
		
		# Kubernetes API and Resources
		self.add_pattern(r'(?i)/api/v1|/apis/apps/v1', description='Kubernetes API endpoints detected - check for unauthorized access')
		self.add_pattern(r'(?i)serviceaccount.*token|k8s.*token', description='CRITICAL: Kubernetes service account token exposed')
		self.add_pattern(r'(?i)namespace|ns=|kubectl.*namespace', description='Kubernetes namespace detected - multi-tenancy component')
		self.add_pattern(r'(?i)deployment|replica.*set|daemon.*set', description='Kubernetes workload objects detected')
		self.add_pattern(r'(?i)configmap|secret|k8s.*secret', description='Kubernetes configuration objects detected - may contain sensitive data')
		self.add_pattern(r'(?i)ingress|ingress.*controller', description='Kubernetes Ingress detected - external access management')
		
		# Kubernetes Distributions and Platforms
		self.add_pattern(r'(?i)openshift|oc.*cluster|okd', description='Red Hat OpenShift detected - enterprise Kubernetes platform')
		self.add_pattern(r'(?i)rancher|rancher\.com', description='Rancher detected - Kubernetes management platform')
		self.add_pattern(r'(?i)eks|elastic.*kubernetes|aws.*eks', description='Amazon EKS detected - managed Kubernetes service')
		self.add_pattern(r'(?i)gke|google.*kubernetes|gcp.*gke', description='Google GKE detected - managed Kubernetes service')
		self.add_pattern(r'(?i)azure.*kubernetes|microsoft.*aks', description='Azure AKS detected - managed Kubernetes service')
		self.add_pattern(r'(?i)k3s|k3s\.io', description='K3s detected - lightweight Kubernetes distribution')
		self.add_pattern(r'(?i)microk8s|canonical.*kubernetes', description='MicroK8s detected - single-node Kubernetes')
		self.add_pattern(r'(?i)kind|kubernetes.*in.*docker', description='KIND detected - Kubernetes in Docker for testing')
		self.add_pattern(r'(?i)minikube', description='Minikube detected - local Kubernetes development')
		
		# === CLOUD PLATFORMS & SERVICES ===
		
		# Amazon Web Services (AWS)
		self.add_pattern(r'(?i)aws.*lambda|lambda\.amazonaws', description='AWS Lambda detected - serverless compute platform')
		self.add_pattern(r'(?i)amazonaws\.com|aws.*api', description='AWS service detected - Amazon Web Services infrastructure')
		self.add_pattern(r'(?i)ec2.*metadata|169\.254\.169\.254', description='CRITICAL: AWS EC2 metadata service accessible - potential credential exposure')
		self.add_pattern(r'(?i)s3\.amazonaws|s3.*bucket', description='AWS S3 storage detected - check for public bucket access')
		self.add_pattern(r'(?i)iam.*role|aws.*role', description='AWS IAM role detected - check for privilege escalation')
		self.add_pattern(r'(?i)cloudformation|cfn.*template', description='AWS CloudFormation detected - infrastructure as code')
		self.add_pattern(r'(?i)elastic.*beanstalk|eb.*environment', description='AWS Elastic Beanstalk detected - application platform')
		self.add_pattern(r'(?i)ecs.*fargate|ecs.*cluster', description='AWS ECS/Fargate detected - container orchestration service')
		
		# Google Cloud Platform (GCP)
		self.add_pattern(r'(?i)googleapis\.com|gcp.*api', description='Google Cloud Platform service detected')
		self.add_pattern(r'(?i)compute\.metadata|metadata\.google', description='CRITICAL: GCP metadata service accessible - potential credential exposure')
		self.add_pattern(r'(?i)cloud\.google|gcloud', description='Google Cloud Platform detected')
		self.add_pattern(r'(?i)app.*engine|gae', description='Google App Engine detected - serverless application platform')
		self.add_pattern(r'(?i)cloud.*functions|gcf', description='Google Cloud Functions detected - serverless compute')
		self.add_pattern(r'(?i)cloud.*run|grun', description='Google Cloud Run detected - containerized serverless platform')
		
		# Microsoft Azure
		self.add_pattern(r'(?i)azure\.com|azure.*api', description='Microsoft Azure service detected')
		self.add_pattern(r'(?i)metadata\.azure|azure.*metadata', description='CRITICAL: Azure metadata service accessible - potential credential exposure')
		self.add_pattern(r'(?i)app.*service|azurewebsites', description='Azure App Service detected - web application platform')
		self.add_pattern(r'(?i)functions.*azure|azure.*functions', description='Azure Functions detected - serverless compute platform')
		self.add_pattern(r'(?i)container.*instances|aci', description='Azure Container Instances detected - serverless containers')
		
		# === SERVERLESS & FUNCTION PLATFORMS ===
		
		# Serverless Frameworks
		self.add_pattern(r'(?i)serverless|sls.*framework', description='Serverless Framework detected - multi-cloud deployment tool')
		self.add_pattern(r'(?i)netlify.*functions|netlify.*edge', description='Netlify Functions detected - edge computing platform')
		self.add_pattern(r'(?i)vercel|zeit.*now', description='Vercel platform detected - frontend deployment and edge functions')
		self.add_pattern(r'(?i)cloudflare.*workers|cf.*workers', description='Cloudflare Workers detected - edge computing platform')
		self.add_pattern(r'(?i)deno.*deploy|deno.*fresh', description='Deno Deploy detected - JavaScript/TypeScript edge platform')
		
		# OpenFaaS and Function Platforms
		self.add_pattern(r'(?i)openfaas|faas.*netes', description='OpenFaaS detected - functions-as-a-service platform')
		self.add_pattern(r'(?i)knative|knative.*serving', description='Knative detected - Kubernetes serverless platform')
		self.add_pattern(r'(?i)nuclio|nuclio\.io', description='Nuclio detected - high-performance serverless platform')
		self.add_pattern(r'(?i)fission|fission\.io', description='Fission detected - Kubernetes-native serverless framework')
		
		# === SERVICE MESH & NETWORKING ===
		
		# Service Mesh Technologies
		self.add_pattern(r'(?i)istio|istio.*mesh', description='Istio service mesh detected - microservices communication platform')
		self.add_pattern(r'(?i)linkerd|linkerd\.io', description='Linkerd service mesh detected - lightweight service mesh')
		self.add_pattern(r'(?i)consul.*connect|consul.*mesh', description='Consul Connect detected - HashiCorp service mesh')
		self.add_pattern(r'(?i)envoy.*proxy|envoyproxy', description='Envoy Proxy detected - cloud-native edge/service proxy')
		self.add_pattern(r'(?i)nginx.*mesh|nginx.*ingress', description='NGINX service mesh/ingress detected')
		self.add_pattern(r'(?i)traefik|traefik\.io', description='Traefik detected - cloud-native reverse proxy and load balancer')
		
		# API Gateways
		self.add_pattern(r'(?i)kong|kong.*gateway', description='Kong API Gateway detected - microservices API management')
		self.add_pattern(r'(?i)ambassador|getambassador', description='Ambassador API Gateway detected - Kubernetes-native gateway')
		self.add_pattern(r'(?i)zuul|netflix.*zuul', description='Netflix Zuul detected - API gateway service')
		self.add_pattern(r'(?i)api.*gateway|aws.*api.*gateway', description='API Gateway detected - check for misconfigurations')
		
		# === MONITORING & OBSERVABILITY ===
		
		# Prometheus Ecosystem
		self.add_pattern(r'(?i)prometheus|prom.*metrics', description='Prometheus monitoring detected - check /metrics endpoint for information disclosure')
		self.add_pattern(r'(?i)alertmanager|alert.*manager', description='Prometheus Alertmanager detected - alert handling system')
		self.add_pattern(r'(?i)grafana|grafana\.com', description='Grafana dashboard detected - check default credentials (admin:admin)')
		self.add_pattern(r'(?i)node.*exporter|node.*metrics', description='Prometheus Node Exporter detected - system metrics collection')
		
		# Distributed Tracing
		self.add_pattern(r'(?i)jaeger|jaeger.*tracing', description='Jaeger distributed tracing detected - microservices observability')
		self.add_pattern(r'(?i)zipkin|zipkin.*tracing', description='Zipkin distributed tracing detected - request tracking system')
		self.add_pattern(r'(?i)opentelemetry|otel', description='OpenTelemetry detected - observability framework')
		
		# Logging and Analytics
		self.add_pattern(r'(?i)elasticsearch|elastic.*search', description='Elasticsearch detected - check for unauthorized access and data exposure')
		self.add_pattern(r'(?i)kibana|elastic.*kibana', description='Kibana interface detected - Elasticsearch visualization')
		self.add_pattern(r'(?i)logstash|elastic.*logstash', description='Logstash detected - log processing pipeline')
		self.add_pattern(r'(?i)fluentd|fluent.*bit', description='Fluentd/Fluent Bit detected - log collection and forwarding')
		self.add_pattern(r'(?i)splunk|splunk.*enterprise', description='Splunk detected - log analysis platform')
		
		# === MESSAGE QUEUES & STREAMING ===
		
		# Message Brokers
		self.add_pattern(r'(?i)kafka|apache.*kafka', description='Apache Kafka detected - distributed streaming platform')
		self.add_pattern(r'(?i)rabbitmq|rabbit.*mq', description='RabbitMQ detected - message broker system')
		self.add_pattern(r'(?i)redis.*cluster|redis.*sentinel', description='Redis cluster detected - in-memory data structure store')
		self.add_pattern(r'(?i)nats|nats\.io', description='NATS messaging detected - cloud-native messaging system')
		self.add_pattern(r'(?i)pulsar|apache.*pulsar', description='Apache Pulsar detected - cloud-native messaging')
		
		# Cloud Message Services
		self.add_pattern(r'(?i)sqs|aws.*sqs', description='AWS SQS detected - managed message queuing service')
		self.add_pattern(r'(?i)pubsub|google.*pubsub', description='Google Pub/Sub detected - messaging service')
		self.add_pattern(r'(?i)service.*bus|azure.*servicebus', description='Azure Service Bus detected - enterprise messaging')
		
		# === SECRETS & CONFIGURATION MANAGEMENT ===
		
		# Secrets Management
		self.add_pattern(r'(?i)vault|hashicorp.*vault', description='HashiCorp Vault detected - secrets management system')
		self.add_pattern(r'(?i)sealed.*secrets|bitnami.*sealed', description='Sealed Secrets detected - Kubernetes secrets encryption')
		self.add_pattern(r'(?i)secrets.*manager|aws.*secrets', description='AWS Secrets Manager detected - cloud secrets management')
		self.add_pattern(r'(?i)key.*vault|azure.*keyvault', description='Azure Key Vault detected - cloud key management')
		self.add_pattern(r'(?i)secret.*manager|gcp.*secrets', description='Google Secret Manager detected - cloud secrets storage')
		
		# Configuration Management
		self.add_pattern(r'(?i)consul|hashicorp.*consul', description='HashiCorp Consul detected - service discovery and configuration')
		self.add_pattern(r'(?i)etcd|etcd.*cluster', description='etcd detected - distributed key-value store')
		self.add_pattern(r'(?i)zookeeper|apache.*zookeeper', description='Apache ZooKeeper detected - distributed coordination service')
		
		# === SECURITY & POLICY ===
		
		# Policy and Security
		self.add_pattern(r'(?i)opa|open.*policy.*agent', description='Open Policy Agent detected - policy-based control system')
		self.add_pattern(r'(?i)gatekeeper|opa.*gatekeeper', description='OPA Gatekeeper detected - Kubernetes policy controller')
		self.add_pattern(r'(?i)falco|falco\.org', description='Falco detected - cloud-native runtime security')
		self.add_pattern(r'(?i)aqua.*security|aquasec', description='Aqua Security detected - container security platform')
		self.add_pattern(r'(?i)twistlock|prisma.*cloud', description='Prisma Cloud (Twistlock) detected - container security')
		
		# Certificate Management
		self.add_pattern(r'(?i)cert.*manager|jetstack.*cert', description='cert-manager detected - Kubernetes certificate management')
		self.add_pattern(r'(?i)letsencrypt|acme.*protocol', description='Let\'s Encrypt/ACME detected - automated certificate management')
		
		# === CLOUD-NATIVE DATABASES ===
		
		# Cloud-Native Databases
		self.add_pattern(r'(?i)cockroachdb|cockroach.*labs', description='CockroachDB detected - distributed SQL database')
		self.add_pattern(r'(?i)vitess|vitess\.io', description='Vitess detected - MySQL clustering system for Kubernetes')
		self.add_pattern(r'(?i)tikv|pingcap.*tikv', description='TiKV detected - distributed key-value database')
		self.add_pattern(r'(?i)cassandra|apache.*cassandra', description='Apache Cassandra detected - distributed NoSQL database')
		self.add_pattern(r'(?i)scylladb|scylla.*db', description='ScyllaDB detected - high-performance NoSQL database')
		
		# === CI/CD & GITOPS ===
		
		# GitOps and CD
		self.add_pattern(r'(?i)argocd|argo.*cd', description='ArgoCD detected - GitOps continuous delivery')
		self.add_pattern(r'(?i)flux|flux.*cd|gitops.*toolkit', description='Flux detected - GitOps operator for Kubernetes')
		self.add_pattern(r'(?i)tekton|tekton.*pipelines', description='Tekton detected - cloud-native CI/CD framework')
		self.add_pattern(r'(?i)jenkins.*x|jenkinsfile', description='Jenkins X detected - cloud-native CI/CD for Kubernetes')
		
		# Container Registries
		self.add_pattern(r'(?i)harbor|harbor.*registry', description='Harbor registry detected - cloud-native artifact registry')
		self.add_pattern(r'(?i)quay|quay\.io', description='Quay container registry detected - enterprise container registry')
		self.add_pattern(r'(?i)ecr|elastic.*container.*registry', description='AWS ECR detected - managed container registry')
		self.add_pattern(r'(?i)gcr|google.*container.*registry', description='Google Container Registry detected')
		self.add_pattern(r'(?i)acr|azure.*container.*registry', description='Azure Container Registry detected')

	async def run(self, service):
		# This plugin only provides pattern matching, no active scanning
		service.info(f"☁️ Cloud-native technology detection active for {service.target.address}:{service.port}")
		service.info(f"🐳 Monitoring for containers, orchestration, and modern cloud infrastructure")