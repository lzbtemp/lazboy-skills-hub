# Kubernetes Manifest Reference

Production-ready YAML examples with best practices for resource management, health checking, update strategy, and resilience.

---

## Namespace

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: myapp
  labels:
    app.kubernetes.io/part-of: myapp
```

---

## Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp-api
  namespace: myapp
  labels:
    app.kubernetes.io/name: myapp-api
    app.kubernetes.io/version: "1.0.0"
    app.kubernetes.io/component: api
    app.kubernetes.io/part-of: myapp
    app.kubernetes.io/managed-by: kubectl
spec:
  replicas: 3
  revisionHistoryLimit: 5
  selector:
    matchLabels:
      app.kubernetes.io/name: myapp-api
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1           # Allow 1 extra pod during rollout
      maxUnavailable: 0     # Never reduce below desired count
  template:
    metadata:
      labels:
        app.kubernetes.io/name: myapp-api
        app.kubernetes.io/version: "1.0.0"
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "3000"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: myapp-api
      terminationGracePeriodSeconds: 30
      securityContext:
        runAsNonRoot: true
        runAsUser: 1001
        runAsGroup: 1001
        fsGroup: 1001
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: api
          image: registry.example.com/myapp-api:1.0.0
          imagePullPolicy: IfNotPresent
          ports:
            - name: http
              containerPort: 3000
              protocol: TCP
          env:
            - name: NODE_ENV
              value: "production"
            - name: PORT
              value: "3000"
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: myapp-db-credentials
                  key: url
            - name: REDIS_URL
              valueFrom:
                configMapKeyRef:
                  name: myapp-config
                  key: redis-url
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi
          livenessProbe:
            httpGet:
              path: /health/live
              port: http
            initialDelaySeconds: 15
            periodSeconds: 20
            timeoutSeconds: 5
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /health/ready
              port: http
            initialDelaySeconds: 5
            periodSeconds: 10
            timeoutSeconds: 3
            failureThreshold: 3
          startupProbe:
            httpGet:
              path: /health/live
              port: http
            initialDelaySeconds: 5
            periodSeconds: 5
            failureThreshold: 30     # 30 * 5s = 150s max startup time
          lifecycle:
            preStop:
              exec:
                command: ["/bin/sh", "-c", "sleep 5"]  # Allow in-flight requests to complete
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop:
                - ALL
          volumeMounts:
            - name: tmp
              mountPath: /tmp
            - name: config
              mountPath: /app/config
              readOnly: true
      volumes:
        - name: tmp
          emptyDir: {}
        - name: config
          configMap:
            name: myapp-config
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app.kubernetes.io/name: myapp-api
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchExpressions:
                    - key: app.kubernetes.io/name
                      operator: In
                      values:
                        - myapp-api
                topologyKey: kubernetes.io/hostname
```

### Probe Guidelines

| Probe | Purpose | Failure Action |
|-------|---------|----------------|
| **startupProbe** | App is done initializing | Kill + restart (blocks liveness/readiness) |
| **livenessProbe** | App is not deadlocked | Kill + restart |
| **readinessProbe** | App can serve traffic | Remove from Service endpoints |

- Use `/health/live` for liveness (simple "process is alive" check)
- Use `/health/ready` for readiness (checks DB connections, caches, etc.)
- Always set `startupProbe` for apps with variable startup time
- `preStop` sleep prevents traffic during pod termination

---

## Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: myapp-api
  namespace: myapp
  labels:
    app.kubernetes.io/name: myapp-api
    app.kubernetes.io/component: api
spec:
  type: ClusterIP
  selector:
    app.kubernetes.io/name: myapp-api
  ports:
    - name: http
      port: 80
      targetPort: http    # References the named port on the container
      protocol: TCP
```

---

## Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: myapp-ingress
  namespace: myapp
  labels:
    app.kubernetes.io/name: myapp-api
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
    nginx.ingress.kubernetes.io/rate-limit-connections: "10"
    nginx.ingress.kubernetes.io/rate-limit-rps: "50"
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - api.example.com
      secretName: myapp-tls
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: myapp-api
                port:
                  name: http
```

---

## ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: myapp-config
  namespace: myapp
  labels:
    app.kubernetes.io/name: myapp-api
data:
  redis-url: "redis://redis-master.myapp.svc.cluster.local:6379"
  log-level: "info"
  feature-flags: |
    {
      "new_dashboard": true,
      "beta_api": false
    }
---
# File-based config
apiVersion: v1
kind: ConfigMap
metadata:
  name: myapp-nginx-config
  namespace: myapp
data:
  nginx.conf: |
    server {
      listen 80;
      location / {
        proxy_pass http://myapp-api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
      }
    }
```

---

## Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: myapp-db-credentials
  namespace: myapp
  labels:
    app.kubernetes.io/name: myapp-api
type: Opaque
# Values must be base64-encoded
# echo -n 'postgres://user:pass@db:5432/myapp' | base64
data:
  url: cG9zdGdyZXM6Ly91c2VyOnBhc3NAZGI6NTQzMi9teWFwcA==
  username: dXNlcg==
  password: cGFzcw==
```

**Production recommendation**: Use an external secret manager (AWS Secrets Manager, HashiCorp Vault) with the External Secrets Operator or Sealed Secrets instead of plain Kubernetes Secrets.

---

## Horizontal Pod Autoscaler (HPA)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: myapp-api
  namespace: myapp
  labels:
    app.kubernetes.io/name: myapp-api
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: myapp-api
  minReplicas: 3
  maxReplicas: 20
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300    # Wait 5min before scaling down
      policies:
        - type: Percent
          value: 25                      # Scale down at most 25% at a time
          periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 30
      policies:
        - type: Percent
          value: 100                     # Double pods if needed
          periodSeconds: 60
        - type: Pods
          value: 4                       # Or add up to 4 pods
          periodSeconds: 60
      selectPolicy: Max
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
    - type: Pods
      pods:
        metric:
          name: http_requests_per_second
        target:
          type: AverageValue
          averageValue: "1000"
```

---

## Pod Disruption Budget (PDB)

Ensures a minimum number of pods remain available during voluntary disruptions (node drain, cluster upgrade, deployment rollout).

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: myapp-api
  namespace: myapp
  labels:
    app.kubernetes.io/name: myapp-api
spec:
  # Use ONE of the following (not both):
  minAvailable: 2            # At least 2 pods must remain running
  # maxUnavailable: 1        # At most 1 pod can be unavailable
  selector:
    matchLabels:
      app.kubernetes.io/name: myapp-api
```

### PDB Guidelines

| Replicas | Recommended PDB |
|----------|----------------|
| 1 | Do not use PDB (blocks node drain) |
| 2 | `maxUnavailable: 1` |
| 3+ | `minAvailable: 2` or `maxUnavailable: 1` |
| Stateful workloads | `maxUnavailable: 1` (conservative) |

---

## NetworkPolicy

Restrict traffic to only what is needed.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: myapp-api-netpol
  namespace: myapp
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: myapp-api
  policyTypes:
    - Ingress
    - Egress
  ingress:
    # Allow traffic from the ingress controller
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: ingress-nginx
          podSelector:
            matchLabels:
              app.kubernetes.io/name: ingress-nginx
      ports:
        - port: 3000
          protocol: TCP
    # Allow traffic from within the namespace (e.g., other microservices)
    - from:
        - podSelector: {}
      ports:
        - port: 3000
          protocol: TCP
  egress:
    # Allow DNS resolution
    - to:
        - namespaceSelector: {}
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - port: 53
          protocol: UDP
        - port: 53
          protocol: TCP
    # Allow database access
    - to:
        - podSelector:
            matchLabels:
              app.kubernetes.io/name: postgresql
      ports:
        - port: 5432
          protocol: TCP
    # Allow Redis access
    - to:
        - podSelector:
            matchLabels:
              app.kubernetes.io/name: redis
      ports:
        - port: 6379
          protocol: TCP
    # Allow external HTTPS (for third-party APIs)
    - to:
        - ipBlock:
            cidr: 0.0.0.0/0
            except:
              - 10.0.0.0/8
              - 172.16.0.0/12
              - 192.168.0.0/16
      ports:
        - port: 443
          protocol: TCP
```

---

## ServiceAccount

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: myapp-api
  namespace: myapp
  labels:
    app.kubernetes.io/name: myapp-api
  annotations:
    # For AWS IRSA (IAM Roles for Service Accounts)
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/myapp-api-role
automountServiceAccountToken: false   # Explicit opt-in per pod if needed
```

---

## Resource Sizing Guide

| Workload Type | CPU Request | CPU Limit | Memory Request | Memory Limit |
|--------------|-------------|-----------|----------------|--------------|
| Node.js API | 100m | 500m | 128Mi | 512Mi |
| Python API | 100m | 1000m | 256Mi | 1Gi |
| Java API | 500m | 2000m | 512Mi | 2Gi |
| Worker/Queue | 200m | 1000m | 256Mi | 1Gi |
| Frontend (nginx) | 50m | 200m | 64Mi | 128Mi |
| Database proxy | 50m | 200m | 64Mi | 256Mi |

**Rules**:
- Always set requests (used for scheduling)
- Set memory limits equal to or slightly above requests to prevent OOMKill
- Consider not setting CPU limits to avoid throttling (use requests for fair scheduling)
- Use VPA (Vertical Pod Autoscaler) in recommendation mode to right-size over time

---

## Label Conventions

Follow the Kubernetes recommended labels:

| Label | Description | Example |
|-------|-------------|---------|
| `app.kubernetes.io/name` | Application name | `myapp-api` |
| `app.kubernetes.io/version` | Application version | `1.0.0` |
| `app.kubernetes.io/component` | Component within architecture | `api`, `worker`, `frontend` |
| `app.kubernetes.io/part-of` | Higher-level application | `myapp` |
| `app.kubernetes.io/managed-by` | Tool managing the resource | `helm`, `kubectl`, `argocd` |
| `app.kubernetes.io/instance` | Instance identifier | `myapp-prod` |

---

## Production Checklist

- [ ] Resource requests and limits are set for all containers
- [ ] Liveness, readiness, and startup probes are configured
- [ ] Rolling update strategy with `maxUnavailable: 0`
- [ ] PodDisruptionBudget is defined
- [ ] Pod anti-affinity spreads replicas across nodes
- [ ] Topology spread constraints distribute across zones
- [ ] NetworkPolicy restricts ingress and egress
- [ ] Secrets use external secret management
- [ ] Security context: non-root, read-only filesystem, drop all capabilities
- [ ] ServiceAccount with minimal permissions
- [ ] HPA is configured with appropriate metrics
- [ ] Image tag is immutable (no `latest`)
- [ ] `terminationGracePeriodSeconds` matches app shutdown time
- [ ] `preStop` hook allows in-flight requests to complete
