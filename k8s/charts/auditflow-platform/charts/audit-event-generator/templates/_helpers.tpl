{{/*
Expand the name of the chart.
*/}}
{{- define "audit-event-generator.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "audit-event-generator.fullname" -}}
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
{{- define "audit-event-generator.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "audit-event-generator.labels" -}}
helm.sh/chart: {{ include "audit-event-generator.chart" . }}
{{ include "audit-event-generator.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "audit-event-generator.selectorLabels" -}}
app.kubernetes.io/name: {{ include "audit-event-generator.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "audit-event-generator.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "audit-event-generator.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}


{{- define "wait-for" -}}
- name: wait-for-{{ .Name }}
  image: busybox:latest
  command:
    - sh
    - -c
    - |
{{ include "wait-for.command" . | nindent 6 }}
{{- end }}

{{- define "wait-for.command" -}}
until (nslookup {{ .Context.Release.Name }}-{{ .Name }}.{{ .Context.Release.Namespace }}.svc.cluster.local >/dev/null 2>&1 ) && \
      timeout 3 nc -z -v {{ .Context.Release.Name }}-{{ .Name }}.{{ .Context.Release.Namespace }}.svc.cluster.local {{ .Port }}; do
  echo "waiting for {{ .Name }} (host: {{ .Context.Release.Name }}-{{ .Name }}.{{ .Context.Release.Namespace }}.svc.cluster.local) on port {{ .Port }}"
  sleep 3
done;
{{- end }}
