"""
AI-powered Report Generator using Groq.
Generates detailed analysis reports for detected anomalies.
"""

import logging
import json
from datetime import datetime
import psycopg2

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

import config
from analysis_engine import ContextAnalyzer, get_anomaly_details


class ReportGenerator:
    """Generates detailed anomaly analysis reports using Groq AI."""

    def __init__(self, api_key=None):
        """Initialize the report generator.
        
        Args:
            api_key: Groq API key (default from config/environment)
        """
        self.api_key = api_key or config.GROQ_API_KEY
        self.model = config.AI_MODEL
        self.base_url = config.GROQ_BASE_URL
        self.logger = logging.getLogger(__name__)
        self.analyzer = ContextAnalyzer()
        self.client = None
        
        # Initialize the Groq client
        if OPENAI_AVAILABLE and self.api_key and self.api_key.startswith('gsk_'):
            try:
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
                self.logger.info(f"Groq client initialized with model: {self.model}")
            except Exception as e:
                self.logger.error(f"Failed to initialize Groq client: {e}")
                self.client = None

    def _build_prompt(self, anomaly_data, analysis_summary):
        """Build the ChatGPT prompt for analysis.
        
        Args:
            anomaly_data: Dict with anomaly detection details
            analysis_summary: Dict from ContextAnalyzer.generate_analysis_summary()
            
        Returns:
            str: The formatted prompt
        """
        # Extract key information
        detected_sensors = anomaly_data.get('detected_sensors', [])
        anomaly_score = anomaly_data.get('anomaly_score', 0)
        detection_method = anomaly_data.get('detection_method', 'isolation_forest')
        
        # Get top deviations
        top_deviations = analysis_summary.get('patterns', {}).get('top_deviations', [])
        
        # Get significant correlations
        correlations = analysis_summary.get('correlations', {}).get('significant', [])
        
        # Format the anomaly reading
        anomaly_reading = analysis_summary.get('context', {}).get('anomaly', {})
        
        # Build deviation summary
        deviation_text = ""
        for dev in top_deviations[:10]:
            deviation_text += f"  - {dev['sensor']}: {dev['anomaly_value']}{dev['unit']} "
            deviation_text += f"(baseline: {dev['baseline_mean']}{dev['unit']}, "
            deviation_text += f"z-score: {dev['z_score']}, change: {dev['percent_change']}%)\n"
        
        # Build correlation summary
        correlation_text = ""
        for corr in correlations[:10]:
            correlation_text += f"  - {corr['sensor1']} ↔ {corr['sensor2']}: "
            correlation_text += f"r={corr['correlation']} ({corr['strength']})\n"
        
        # Build context summary
        before_count = len(analysis_summary.get('context', {}).get('before', []))
        after_count = len(analysis_summary.get('context', {}).get('after', []))
        
        prompt = f"""You are an industrial sensor data analyst expert. Analyze the following anomaly detected in a manufacturing/industrial sensor system.

## ANOMALY DETECTION DETAILS
- Detection Method: {detection_method}
- Anomaly Score: {anomaly_score:.4f} (lower/more negative = more anomalous)
- Timestamp: {anomaly_reading.get('timestamp', 'N/A')}
- Primary Sensors Flagged: {', '.join(detected_sensors) if detected_sensors else 'None specifically identified'}

## SENSOR READINGS AT ANOMALY
The system monitors 50 sensor parameters across 5 categories:
- Environmental (temperature, pressure, humidity, air quality, etc.)
- Mechanical (vibration, RPM, torque, bearing temp, etc.)
- Thermal (coolant temp, exhaust temp, oil temp, etc.)
- Electrical (voltage, current, power factor, frequency, etc.)
- Fluid Dynamics (flow rate, fluid pressure, pump efficiency, etc.)

## TOP 10 PARAMETER DEVIATIONS FROM BASELINE
(Sorted by z-score magnitude - how many standard deviations from normal)
{deviation_text if deviation_text else "No significant deviations detected"}

## SIGNIFICANT PARAMETER CORRELATIONS
(Strong correlations observed in the data window)
{correlation_text if correlation_text else "No significant correlations found"}

## CONTEXT WINDOW
- Readings analyzed before anomaly: {before_count}
- Readings analyzed after anomaly: {after_count}

---

Based on this data, provide a comprehensive analysis report with the following sections:

### 1. ROOT CAUSE ANALYSIS
Explain the most likely root cause(s) of this anomaly based on the sensor deviations and correlations. Consider:
- Which sensor categories are most affected?
- Are the correlated parameters suggesting a specific system failure mode?
- Is this a sudden spike or part of a degradation pattern?

### 2. AFFECTED SYSTEMS
List the specific systems or components that are likely affected and explain how the sensor readings indicate this.

### 3. SEVERITY ASSESSMENT
Rate the severity (Critical/High/Medium/Low) and explain the potential impact if left unaddressed.

### 4. PREVENTION RECOMMENDATIONS
Provide specific, actionable recommendations to prevent this type of anomaly in the future, including:
- Maintenance actions
- Monitoring thresholds to adjust
- Process changes to consider

### 5. IMMEDIATE ACTIONS REQUIRED
List any immediate actions that should be taken right now to address this anomaly.

Format your response in clear markdown with headers and bullet points for readability."""

        return prompt

    def _call_ai(self, prompt):
        """Call the Groq AI API to generate analysis.
        
        Args:
            prompt: The analysis prompt
            
        Returns:
            str: The generated analysis text
        """
        if not OPENAI_AVAILABLE:
            self.logger.warning("OpenAI library not available")
            return self._generate_fallback_report(prompt)
        
        if not self.client:
            self.logger.warning("Groq API client not initialized - check API key")
            return self._generate_fallback_report(prompt)
        
        try:
            self.logger.info(f"Calling Groq API with model: {self.model}")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert industrial sensor data analyst specializing in predictive maintenance and anomaly detection. Provide detailed, actionable analysis."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=4000  # Groq supports larger outputs
            )
            
            self.logger.info("Groq API response received successfully")
            return response.choices[0].message.content
            
        except Exception as e:
            self.logger.error(f"Groq API call failed: {e}")
            return self._generate_fallback_report(prompt)

    def _generate_fallback_report(self, prompt):
        """Generate a basic report when ChatGPT is unavailable.
        
        Args:
            prompt: The original prompt (for extracting data)
            
        Returns:
            str: A basic analysis report
        """
        return """## Automated Analysis Report

**Note:** This is an automated fallback report. ChatGPT API is not available or not configured.

### 1. ROOT CAUSE ANALYSIS
Based on the sensor deviations detected, this anomaly appears to involve multiple parameters exceeding their normal operating ranges. Further investigation is recommended to determine the specific root cause.

### 2. AFFECTED SYSTEMS
Review the flagged sensors in the anomaly detection to identify which systems require attention. Pay particular attention to sensors with high z-scores (>2.0).

### 3. SEVERITY ASSESSMENT
**Severity: To Be Determined**
Manual review of the sensor data is recommended to assess the actual severity level.

### 4. PREVENTION RECOMMENDATIONS
- Review and potentially adjust monitoring thresholds for flagged sensors
- Implement regular maintenance schedules for affected equipment
- Consider adding redundant sensors for critical parameters
- Document this incident for future reference

### 5. IMMEDIATE ACTIONS REQUIRED
- Verify current sensor readings are within safe operating limits
- Check for any physical signs of equipment stress or damage
- Review recent operational changes that may have contributed
- Consult with maintenance team if readings remain abnormal

---
*To enable AI-powered analysis, configure your OpenAI API key in the OPENAI_API_KEY environment variable.*"""

    def _extract_sections(self, analysis_text):
        """Extract root cause and recommendations from the analysis.
        
        Args:
            analysis_text: The full ChatGPT response
            
        Returns:
            tuple: (root_cause, prevention_recommendations)
        """
        root_cause = ""
        prevention = ""
        
        lines = analysis_text.split('\n')
        current_section = None
        
        for line in lines:
            line_lower = line.lower().strip()
            
            if 'root cause' in line_lower:
                current_section = 'root_cause'
                continue
            elif 'prevention' in line_lower:
                current_section = 'prevention'
                continue
            elif 'affected systems' in line_lower or 'severity' in line_lower or 'immediate actions' in line_lower:
                current_section = None
                continue
            
            if current_section == 'root_cause':
                root_cause += line + '\n'
            elif current_section == 'prevention':
                prevention += line + '\n'
        
        return root_cause.strip(), prevention.strip()

    def generate_report(self, anomaly_id):
        """Generate a complete analysis report for an anomaly.
        
        Args:
            anomaly_id: ID from anomaly_detections table
            
        Returns:
            dict with report data, or None on failure
        """
        # Get anomaly details
        anomaly_data = get_anomaly_details(anomaly_id)
        if not anomaly_data:
            self.logger.error(f"Anomaly {anomaly_id} not found")
            return None
        
        reading_id = anomaly_data['reading_id']
        detected_sensors = anomaly_data.get('detected_sensors', [])
        
        # Generate analysis summary
        analysis_summary = self.analyzer.generate_analysis_summary(
            reading_id, 
            detected_sensors
        )
        
        if not analysis_summary:
            self.logger.error(f"Failed to generate analysis summary for reading {reading_id}")
            return None
        
        # Build prompt and call AI
        prompt = self._build_prompt(anomaly_data, analysis_summary)
        chatgpt_analysis = self._call_ai(prompt)
        
        # Extract sections
        root_cause, prevention = self._extract_sections(chatgpt_analysis)
        
        return {
            'anomaly_id': anomaly_id,
            'reading_id': reading_id,
            'context_data': analysis_summary.get('context'),
            'correlations': analysis_summary.get('correlations'),
            'chatgpt_analysis': chatgpt_analysis,
            'root_cause': root_cause,
            'prevention_recommendations': prevention
        }

    def save_report(self, report_data):
        """Save a generated report to the database.
        
        Args:
            report_data: Dict from generate_report()
            
        Returns:
            int: ID of the saved report, or None on failure
        """
        conn = None
        try:
            conn = psycopg2.connect(**config.DB_CONFIG)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO analysis_reports 
                    (anomaly_id, context_data, correlations, chatgpt_analysis, 
                     root_cause, prevention_recommendations, status, completed_at)
                VALUES (%s, %s, %s, %s, %s, %s, 'completed', NOW())
                RETURNING id
            """, (
                report_data['anomaly_id'],
                json.dumps(report_data.get('context_data')),
                json.dumps(report_data.get('correlations')),
                report_data.get('chatgpt_analysis'),
                report_data.get('root_cause'),
                report_data.get('prevention_recommendations')
            ))
            
            report_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            
            self.logger.info(f"Saved report {report_id} for anomaly {report_data['anomaly_id']}")
            return report_id
            
        except Exception as e:
            self.logger.error(f"Failed to save report: {e}")
            if conn:
                conn.rollback()
            return None
        finally:
            if conn:
                conn.close()

    def generate_and_save_report(self, anomaly_id):
        """Generate and save a report in one call.
        
        Args:
            anomaly_id: ID from anomaly_detections table
            
        Returns:
            tuple: (report_id, report_data) or (None, None) on failure
        """
        # Mark as generating
        self._update_report_status(anomaly_id, 'generating')
        
        report_data = self.generate_report(anomaly_id)
        if not report_data:
            self._update_report_status(anomaly_id, 'failed')
            return None, None
        
        report_id = self.save_report(report_data)
        if not report_id:
            return None, report_data
        
        report_data['id'] = report_id
        return report_id, report_data

    def _update_report_status(self, anomaly_id, status):
        """Update or create a report status entry."""
        conn = None
        try:
            conn = psycopg2.connect(**config.DB_CONFIG)
            cursor = conn.cursor()
            
            # Check if report exists
            cursor.execute("""
                SELECT id FROM analysis_reports WHERE anomaly_id = %s
            """, (anomaly_id,))
            
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute("""
                    UPDATE analysis_reports SET status = %s WHERE anomaly_id = %s
                """, (status, anomaly_id))
            else:
                cursor.execute("""
                    INSERT INTO analysis_reports (anomaly_id, status)
                    VALUES (%s, %s)
                """, (anomaly_id, status))
            
            conn.commit()
            cursor.close()
            
        except Exception as e:
            self.logger.error(f"Failed to update report status: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()


def get_report(report_id):
    """Fetch a report from the database.
    
    Args:
        report_id: ID of the report
        
    Returns:
        dict with report data or None
    """
    conn = None
    try:
        conn = psycopg2.connect(**config.DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, anomaly_id, context_data, correlations, 
                   chatgpt_analysis, root_cause, prevention_recommendations,
                   status, created_at, completed_at
            FROM analysis_reports
            WHERE id = %s
        """, (report_id,))
        
        row = cursor.fetchone()
        cursor.close()
        
        if not row:
            return None
        
        return {
            'id': row[0],
            'anomaly_id': row[1],
            'context_data': row[2],
            'correlations': row[3],
            'chatgpt_analysis': row[4],
            'root_cause': row[5],
            'prevention_recommendations': row[6],
            'status': row[7],
            'created_at': str(row[8]),
            'completed_at': str(row[9]) if row[9] else None
        }
        
    except Exception as e:
        logging.error(f"Failed to fetch report: {e}")
        return None
    finally:
        if conn:
            conn.close()


def get_report_by_anomaly(anomaly_id):
    """Fetch a report by anomaly ID.
    
    Args:
        anomaly_id: ID from anomaly_detections table
        
    Returns:
        dict with report data or None
    """
    conn = None
    try:
        conn = psycopg2.connect(**config.DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, anomaly_id, context_data, correlations, 
                   chatgpt_analysis, root_cause, prevention_recommendations,
                   status, created_at, completed_at
            FROM analysis_reports
            WHERE anomaly_id = %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (anomaly_id,))
        
        row = cursor.fetchone()
        cursor.close()
        
        if not row:
            return None
        
        return {
            'id': row[0],
            'anomaly_id': row[1],
            'context_data': row[2],
            'correlations': row[3],
            'chatgpt_analysis': row[4],
            'root_cause': row[5],
            'prevention_recommendations': row[6],
            'status': row[7],
            'created_at': str(row[8]),
            'completed_at': str(row[9]) if row[9] else None
        }
        
    except Exception as e:
        logging.error(f"Failed to fetch report by anomaly: {e}")
        return None
    finally:
        if conn:
            conn.close()


class FullSessionReportGenerator:
    """Generates comprehensive reports for entire monitoring sessions."""
    
    def __init__(self, api_key=None):
        self.api_key = api_key or config.GROQ_API_KEY
        self.model = config.AI_MODEL
        self.base_url = config.GROQ_BASE_URL
        self.logger = logging.getLogger(__name__)
        self.client = None
        
        if OPENAI_AVAILABLE and self.api_key and self.api_key.startswith('gsk_'):
            try:
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
                self.logger.info(f"FullSessionReportGenerator: Groq client ready")
            except Exception as e:
                self.logger.error(f"Failed to initialize Groq client: {e}")
    
    def get_all_session_anomalies(self):
        """Fetch all anomalies from the current session."""
        conn = None
        try:
            conn = psycopg2.connect(**config.DB_CONFIG)
            cursor = conn.cursor()
            
            # Get all anomalies with their sensor readings
            cursor.execute("""
                SELECT 
                    ad.id, ad.reading_id, ad.detection_method, ad.anomaly_score,
                    ad.detected_sensors, ad.created_at,
                    sr.timestamp, sr.rpm, sr.temperature, sr.vibration, sr.pressure,
                    sr.humidity, sr.bearing_temp, sr.oil_temp, sr.coolant_temp,
                    sr.motor_current, sr.voltage, sr.current, sr.power_factor,
                    sr.flow_rate, sr.noise_level, sr.thermal_efficiency
                FROM anomaly_detections ad
                JOIN sensor_readings sr ON ad.reading_id = sr.id
                WHERE ad.is_anomaly = true
                ORDER BY ad.created_at ASC
            """)
            
            columns = [desc[0] for desc in cursor.description]
            anomalies = [dict(zip(columns, row)) for row in cursor.fetchall()]
            cursor.close()
            
            # Convert timestamps to strings
            for a in anomalies:
                if 'created_at' in a and a['created_at']:
                    a['created_at'] = str(a['created_at'])
                if 'timestamp' in a and a['timestamp']:
                    a['timestamp'] = str(a['timestamp'])
            
            return anomalies
            
        except Exception as e:
            self.logger.error(f"Failed to fetch session anomalies: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def get_session_stats(self):
        """Get overall session statistics."""
        conn = None
        try:
            conn = psycopg2.connect(**config.DB_CONFIG)
            cursor = conn.cursor()
            
            # Total readings
            cursor.execute("SELECT COUNT(*) FROM sensor_readings")
            total_readings = cursor.fetchone()[0]
            
            # Total anomalies
            cursor.execute("SELECT COUNT(*) FROM anomaly_detections WHERE is_anomaly = true")
            total_anomalies = cursor.fetchone()[0]
            
            # Time range
            cursor.execute("""
                SELECT MIN(timestamp), MAX(timestamp) FROM sensor_readings
            """)
            time_range = cursor.fetchone()
            
            # Most common anomaly sensors
            cursor.execute("""
                SELECT unnest(detected_sensors) as sensor, COUNT(*) as count
                FROM anomaly_detections
                WHERE is_anomaly = true AND detected_sensors IS NOT NULL
                GROUP BY sensor
                ORDER BY count DESC
                LIMIT 15
            """)
            top_sensors = [{'sensor': row[0], 'count': row[1]} for row in cursor.fetchall()]
            
            # Severity distribution (based on anomaly score)
            cursor.execute("""
                SELECT 
                    CASE 
                        WHEN anomaly_score < -0.05 THEN 'critical'
                        WHEN anomaly_score < -0.02 THEN 'high'
                        WHEN anomaly_score < -0.01 THEN 'medium'
                        ELSE 'low'
                    END as severity,
                    COUNT(*) as count
                FROM anomaly_detections
                WHERE is_anomaly = true
                GROUP BY severity
            """)
            severity_dist = {row[0]: row[1] for row in cursor.fetchall()}
            
            cursor.close()
            
            return {
                'total_readings': total_readings,
                'total_anomalies': total_anomalies,
                'anomaly_rate': round((total_anomalies / total_readings * 100), 2) if total_readings > 0 else 0,
                'start_time': str(time_range[0]) if time_range[0] else None,
                'end_time': str(time_range[1]) if time_range[1] else None,
                'top_anomaly_sensors': top_sensors,
                'severity_distribution': severity_dist
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get session stats: {e}")
            return {}
        finally:
            if conn:
                conn.close()
    
    def compute_cross_anomaly_correlations(self, anomalies):
        """Find patterns and correlations across all anomalies."""
        if not anomalies:
            return {}
        
        # Sensor co-occurrence matrix
        sensor_pairs = {}
        for anomaly in anomalies:
            sensors = anomaly.get('detected_sensors', []) or []
            for i, s1 in enumerate(sensors):
                for s2 in sensors[i+1:]:
                    pair = tuple(sorted([s1, s2]))
                    sensor_pairs[pair] = sensor_pairs.get(pair, 0) + 1
        
        # Sort by frequency
        top_pairs = sorted(sensor_pairs.items(), key=lambda x: x[1], reverse=True)[:20]
        
        # Time-based patterns (anomalies clustering)
        time_gaps = []
        for i in range(1, len(anomalies)):
            if anomalies[i].get('timestamp') and anomalies[i-1].get('timestamp'):
                # Simple string comparison for now
                time_gaps.append({
                    'from_id': anomalies[i-1]['id'],
                    'to_id': anomalies[i]['id']
                })
        
        return {
            'sensor_co_occurrences': [{'sensors': list(p[0]), 'count': p[1]} for p in top_pairs],
            'anomaly_sequence_count': len(anomalies),
            'cascading_patterns': len([g for g in time_gaps]) if time_gaps else 0
        }
    
    def _build_full_session_prompt(self, stats, anomalies, correlations):
        """Build a comprehensive prompt for full session analysis."""
        
        # Format anomalies summary
        anomaly_summaries = []
        for i, a in enumerate(anomalies[:30]):  # Limit to first 30 for token limits
            sensors = a.get('detected_sensors', []) or []
            anomaly_summaries.append(
                f"  {i+1}. Score: {a.get('anomaly_score', 0):.4f} | "
                f"Sensors: {', '.join(sensors[:5]) if sensors else 'N/A'} | "
                f"RPM: {a.get('rpm', 'N/A')}, Temp: {a.get('temperature', 'N/A')}°F, "
                f"Vibration: {a.get('vibration', 'N/A')}mm/s"
            )
        
        # Format top sensor issues
        sensor_issues = ""
        for s in stats.get('top_anomaly_sensors', [])[:10]:
            sensor_issues += f"  - {s['sensor']}: {s['count']} occurrences\n"
        
        # Format correlations
        corr_text = ""
        for c in correlations.get('sensor_co_occurrences', [])[:10]:
            corr_text += f"  - {c['sensors'][0]} ↔ {c['sensors'][1]}: {c['count']} times together\n"
        
        # Severity breakdown
        sev = stats.get('severity_distribution', {})
        severity_text = f"  Critical: {sev.get('critical', 0)}, High: {sev.get('high', 0)}, Medium: {sev.get('medium', 0)}, Low: {sev.get('low', 0)}"
        
        prompt = f"""You are an expert industrial engineer conducting a comprehensive post-session analysis of a sensor monitoring system. This is a FULL SESSION REPORT covering all anomalies detected during a complete monitoring period.

## SESSION OVERVIEW
- **Total Sensor Readings:** {stats.get('total_readings', 0):,}
- **Total Anomalies Detected:** {stats.get('total_anomalies', 0)}
- **Anomaly Rate:** {stats.get('anomaly_rate', 0)}%
- **Session Start:** {stats.get('start_time', 'N/A')}
- **Session End:** {stats.get('end_time', 'N/A')}

## SEVERITY DISTRIBUTION
{severity_text}

## TOP SENSORS TRIGGERING ANOMALIES
(Sensors most frequently flagged during anomalies)
{sensor_issues if sensor_issues else "  No specific sensors identified"}

## SENSOR CO-OCCURRENCE PATTERNS
(Sensors that frequently trigger anomalies together - indicates systemic issues)
{corr_text if corr_text else "  No significant co-occurrences found"}

## INDIVIDUAL ANOMALY SUMMARY
(First {len(anomaly_summaries)} of {len(anomalies)} total anomalies)
{chr(10).join(anomaly_summaries) if anomaly_summaries else "No anomalies recorded"}

---

Provide a **COMPREHENSIVE FULL SESSION ANALYSIS REPORT** with the following sections:

### 1. EXECUTIVE SUMMARY
Provide a brief overview of the session's health and key findings in 2-3 sentences.

### 2. CRITICAL FINDINGS
List the most critical issues discovered during this session. What needs immediate attention?

### 3. ROOT CAUSE ANALYSIS
Based on the sensor co-occurrences and anomaly patterns:
- What are the likely root causes of the detected anomalies?
- Are there systemic issues indicated by sensor correlations?
- What failure modes might be developing?

### 4. PATTERN ANALYSIS
- Are there temporal patterns (anomalies clustering at certain times)?
- Are certain sensors consistently involved together?
- What does the anomaly rate tell us about system health?

### 5. SYSTEM HEALTH ASSESSMENT
Rate the overall system health (Critical/Poor/Fair/Good/Excellent) and explain why.

### 6. PRIORITIZED RECOMMENDATIONS
Provide specific, prioritized recommendations:
1. **IMMEDIATE** (next 24 hours): Actions to prevent failure
2. **SHORT-TERM** (next week): Maintenance and monitoring changes
3. **LONG-TERM** (next month): Process and equipment improvements

### 7. PREVENTIVE MAINTENANCE SCHEDULE
Based on the anomalies, suggest a preventive maintenance schedule for the key affected systems.

### 8. MONITORING IMPROVEMENTS
Recommend any changes to monitoring thresholds or additional sensors that should be added.

Format your response in clear markdown with headers, bullet points, and tables where appropriate. Be specific and actionable."""

        return prompt
    
    def generate_full_session_report(self):
        """Generate a comprehensive report for the entire session."""
        self.logger.info("Generating full session report...")
        
        # Gather all data
        anomalies = self.get_all_session_anomalies()
        stats = self.get_session_stats()
        correlations = self.compute_cross_anomaly_correlations(anomalies)
        
        if not anomalies:
            return {
                'success': False,
                'error': 'No anomalies found in this session',
                'stats': stats
            }
        
        # Build and call AI
        prompt = self._build_full_session_prompt(stats, anomalies, correlations)
        
        if not self.client:
            analysis = self._generate_fallback_full_report(stats, anomalies, correlations)
        else:
            try:
                self.logger.info(f"Calling Groq API for full session report...")
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert industrial engineer providing comprehensive post-session analysis. Be thorough, specific, and actionable."
                        },
                        {
                            "role": "user", 
                            "content": prompt
                        }
                    ],
                    temperature=0.7,
                    max_tokens=6000
                )
                analysis = response.choices[0].message.content
                self.logger.info("Full session report generated successfully")
            except Exception as e:
                self.logger.error(f"Groq API failed for full report: {e}")
                analysis = self._generate_fallback_full_report(stats, anomalies, correlations)
        
        return {
            'success': True,
            'stats': stats,
            'correlations': correlations,
            'total_anomalies': len(anomalies),
            'analysis': analysis,
            'generated_at': datetime.now().isoformat()
        }
    
    def _generate_fallback_full_report(self, stats, anomalies, correlations):
        """Generate fallback report when AI is unavailable."""
        top_sensors = stats.get('top_anomaly_sensors', [])
        sensor_list = '\n'.join([f"- **{s['sensor']}**: {s['count']} occurrences" for s in top_sensors[:10]]) if top_sensors else 'No specific sensors identified'
        
        # Format severity distribution nicely
        sev = stats.get('severity_distribution', {})
        severity_text = f"""- **Critical:** {sev.get('critical', 0)}
- **High:** {sev.get('high', 0)}
- **Medium:** {sev.get('medium', 0)}
- **Low:** {sev.get('low', 0)}"""
        
        # Format co-occurrences nicely (this will be displayed by the dashboard UI, not in the analysis text)
        cooccurrences = correlations.get('sensor_co_occurrences', [])[:10]
        cooccurrence_text = ""
        if cooccurrences:
            for c in cooccurrences:
                sensors = c.get('sensors', [])
                if len(sensors) >= 2:
                    cooccurrence_text += f"- **{sensors[0]}** ↔ **{sensors[1]}**: {c['count']} times together\n"
        else:
            cooccurrence_text = "No co-occurrence patterns detected"
        
        return f"""# Full Session Analysis Report

**Note:** This is an automated analysis. Configure your Groq API key in config.py for AI-powered insights.

## Session Overview
- **Total Readings:** {stats.get('total_readings', 0):,}
- **Total Anomalies:** {stats.get('total_anomalies', 0)}
- **Anomaly Rate:** {stats.get('anomaly_rate', 0)}%
- **Session Duration:** {stats.get('start_time', 'N/A')} to {stats.get('end_time', 'N/A')}

## Severity Breakdown
{severity_text}

## Top Anomaly-Contributing Sensors
{sensor_list}

## Sensor Correlation Patterns
{cooccurrence_text}

## Automated Recommendations

### Immediate Actions
1. **Review Critical Sensors** - Focus on sensors appearing most frequently in anomalies
2. **Check Correlated Sensors** - Sensors triggering together may indicate systemic issues
3. **Verify Threshold Settings** - Current thresholds may need adjustment based on observed patterns

### Preventive Measures
1. Schedule maintenance for equipment related to high-frequency anomaly sensors
2. Investigate mechanical linkages between co-occurring sensor pairs
3. Review calibration schedules for affected monitoring equipment
4. Consider implementing early warning thresholds at 80% of current limits

### Monitoring Improvements
1. Increase sampling frequency during high-risk operational periods
2. Add redundant sensors for critical measurements
3. Implement trend analysis to detect gradual degradation

---
*For detailed AI-powered root cause analysis, configure GROQ_API_KEY in config.py*"""


def generate_full_session_report():
    """Convenience function to generate a full session report."""
    generator = FullSessionReportGenerator()
    return generator.generate_full_session_report()
