{{/*
Expand the name of the chart.
*/}}
{{- define "auditflow-platform.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "auditflow-platform.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "auditflow-platform.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "auditflow-platform.labels" -}}
helm.sh/chart: {{ include "auditflow-platform.chart" . }}
{{ include "auditflow-platform.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "auditflow-platform.selectorLabels" -}}
app.kubernetes.io/name: {{ include "auditflow-platform.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "auditflow-platform.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "auditflow-platform.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}


{{- define "afp-wait-for" -}}
- name: wait-for-{{ .Name }}
  image: busybox:latest
  command:
    - sh
    - -c
    - |
{{ include "afp-wait-for.command" . | nindent 6 }}
{{- end }}

{{- define "afp-wait-for.command" -}}
until (nslookup {{ .Context.Release.Name }}-{{ .Name }}.{{ .Context.Release.Namespace }}.svc.cluster.local >/dev/null 2>&1 ) && \
      timeout 3 nc -z -v {{ .Context.Release.Name }}-{{ .Name }}.{{ .Context.Release.Namespace }}.svc.cluster.local {{ .Port }}; do
  echo "waiting for {{ .Name }} (host: {{ .Context.Release.Name }}-{{ .Name }}.{{ .Context.Release.Namespace }}.svc.cluster.local) on port {{ .Port }}"
  sleep 3
done;
{{- end }}