import streamlit as st
import pandas as pd
from redactor import PrivacyRedactor, levenshtein_similarity
import time

# Page configuration
st.set_page_config(
    page_title="Privacy Protector - AI Redaction Tool",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .entity-table {
        font-size: 0.8rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
</style>
""", unsafe_allow_html=True)

class PrivacyProtectorApp:
    def __init__(self):
        self.redactor = PrivacyRedactor()
        self.initialize_session_state()
    
    def initialize_session_state(self):
        """Initialize session state variables"""
        if 'redacted_text' not in st.session_state:
            st.session_state.redacted_text = ""
        if 'entities' not in st.session_state:
            st.session_state.entities = []
        if 'original_text' not in st.session_state:
            st.session_state.original_text = ""
        if 'similarity_score' not in st.session_state:
            st.session_state.similarity_score = 0.0

    def render_sidebar(self):
        """Render the sidebar controls"""
        st.sidebar.title("🔧 Configuration")
        
        st.sidebar.markdown("### Redaction Mode")
        mode = st.sidebar.radio(
            "Choose redaction mode:",
            ["Redact", "Mask"],
            help="Redact: Remove sensitive text completely | Mask: Replace with [ENTITY_TYPE]"
        )
        
        st.sidebar.markdown("### Detection Engine")
        use_advanced = st.sidebar.checkbox(
            "Use Advanced AI Detection (spaCy)",
            value=True,
            help="Uses spaCy NLP model for better PERSON, LOCATION, and DATE_TIME detection"
        )
        
        if use_advanced != self.redactor.use_spacy:
            self.redactor = PrivacyRedactor(use_spacy=use_advanced)
        
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📊 Performance Metrics")
        
        if st.session_state.original_text:
            col1, col2 = st.sidebar.columns(2)
            with col1:
                st.metric("Original Length", f"{len(st.session_state.original_text)} chars")
            with col2:
                st.metric("Redacted Length", f"{len(st.session_state.redacted_text)} chars")
            
            st.sidebar.metric("Similarity Score", f"{st.session_state.similarity_score:.2%}")
            st.sidebar.metric("Entities Found", len(st.session_state.entities))
        
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🚀 Quick Actions")
        
        if st.sidebar.button("🔄 Reset All", use_container_width=True):
            self.reset_application()
        
        if st.sidebar.button("📋 Use Sample Text", use_container_width=True):
            self.load_sample_text()
        
        return mode.lower()

    def load_sample_text(self):
        """Load sample text for demonstration"""
        sample_text = """At exactly 96:12 on 03/01/2004, Martin O'Neil checked into a hotel in Coriff after booking a room through https://www.szg-joooling-demons.com.  
The reservation confirmation was sent to martin.oneil@travel-model.com.  
The system recorded his access from IP 81.22.144.19. Hotel staff later called +44 7811 220099 to confirm a payment using card number 4485-9901-6623-3300.

John Smith contacted us from New York with IP 192.168.1.1 and email john.smith@example.com. His phone number is (212) 555-1234 and he used credit card 4111-1111-1111-1111."""
        
        st.session_state.original_text = sample_text

    def reset_application(self):
        """Reset the application state"""
        for key in ['redacted_text', 'entities', 'original_text', 'similarity_score']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    def render_text_input(self):
        """Render the text input section"""
        st.markdown("### 📝 Input Text")
        
        input_method = st.radio(
            "Choose input method:",
            ["Type Text", "Upload File"],
            horizontal=True
        )
        
        if input_method == "Type Text":
            text_input = st.text_area(
                "Enter text to redact:",
                height=200,
                placeholder="Paste or type text containing sensitive information here...",
                value=st.session_state.original_text,
                key="text_input"
            )
            st.session_state.original_text = text_input
            
        else:  # File upload
            uploaded_file = st.file_uploader(
                "Upload a text file",
                type=['txt'],
                help="Upload a .txt file containing text to redact"
            )
            
            if uploaded_file is not None:
                try:
                    text_content = uploaded_file.getvalue().decode("utf-8")
                    st.session_state.original_text = text_content
                    st.success(f"✅ File uploaded successfully! Size: {len(text_content)} characters")
                except Exception as e:
                    st.error(f"Error reading file: {e}")

    def process_redaction(self, mode):
        """Process the redaction and update session state"""
        if not st.session_state.original_text.strip():
            st.warning("⚠️ Please enter some text to redact.")
            return
        
        with st.spinner("🛡️ Scanning for sensitive information..."):
            start_time = time.time()
            
            redacted_text, entities = self.redactor.redact_text(
                st.session_state.original_text, 
                mode
            )
            
            processing_time = time.time() - start_time
            
            # Update session state
            st.session_state.redacted_text = redacted_text
            st.session_state.entities = entities
            st.session_state.similarity_score = levenshtein_similarity(
                st.session_state.original_text, 
                redacted_text
            )
            
            st.success(f"✅ Redaction completed in {processing_time:.2f} seconds!")

    def render_results(self, mode):
        """Render the results section"""
        if not st.session_state.redacted_text:
            return
        
        st.markdown("---")
        st.markdown("## 📊 Results")
        
        # Metrics row
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Original Characters", len(st.session_state.original_text))
        with col2:
            st.metric("Redacted Characters", len(st.session_state.redacted_text))
        with col3:
            st.metric("Entities Redacted", len(st.session_state.entities))
        with col4:
            st.metric("Processing Similarity", f"{st.session_state.similarity_score:.2%}")
        
        # Text comparison
        st.markdown("### 🔍 Text Comparison")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Original Text")
            st.text_area(
                "Original",
                st.session_state.original_text,
                height=250,
                key="original_display",
                label_visibility="collapsed"
            )
        
        with col2:
            st.markdown("#### Redacted Text")
            st.text_area(
                "Redacted",
                st.session_state.redacted_text,
                height=250,
                key="redacted_display",
                label_visibility="collapsed"
            )
        
        # Entities table
        if st.session_state.entities:
            st.markdown("### 🎯 Detected Entities")
            
            # Convert to DataFrame for better display
            df_entities = pd.DataFrame(st.session_state.entities)
            
            # Display entity counts
            entity_counts = df_entities['entity_type'].value_counts()
            st.markdown("**Entity Distribution:**")
            for entity_type, count in entity_counts.items():
                st.write(f"- {entity_type}: {count}")
            
            # Show detailed table
            st.dataframe(
                df_entities,
                use_container_width=True,
                column_config={
                    "entity_type": "Entity Type",
                    "text": "Extracted Text", 
                    "start": "Start Index",
                    "end": "End Index"
                }
            )
            
            # Download options
            st.markdown("### 💾 Export Results")
            col1, col2 = st.columns(2)
            
            with col1:
                st.download_button(
                    label="📥 Download Redacted Text",
                    data=st.session_state.redacted_text,
                    file_name="redacted_output.txt",
                    mime="text/plain",
                    use_container_width=True
                )
            
            with col2:
                # Convert entities to CSV for download
                if not df_entities.empty:
                    csv_data = df_entities.to_csv(index=False)
                    st.download_button(
                        label="📊 Download Entities CSV",
                        data=csv_data,
                        file_name="detected_entities.csv",
                        mime="text/csv",
                        use_container_width=True
                    )

    def run(self):
        """Main application runner"""
        # Header
        st.markdown('<div class="main-header">🛡️ Privacy Protector - AI Redaction Tool</div>', unsafe_allow_html=True)
        st.markdown("Automatically detect and redact sensitive information from text using AI and rule-based systems.")
        
        # Sidebar
        mode = self.render_sidebar()
        
        # Main content
        self.render_text_input()
        
        # Process button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button(
                f"🚀 Start Redaction ({mode.title()} Mode)", 
                use_container_width=True,
                type="primary"
            ):
                self.process_redaction(mode)
        
        # Results
        self.render_results(mode)
        
        # Footer
        st.markdown("---")
        st.markdown(
            "**Built for Cybersecurity Hackathon** | "
            "Uses Hybrid AI (spaCy + Rule-based) Detection | "
            "Supports 8 Entity Types: PERSON, LOCATION, EMAIL, IP, PHONE, CREDIT_CARD, DATE_TIME, URL"
        )

# Run the application
if __name__ == "__main__":
    app = PrivacyProtectorApp()
    app.run()