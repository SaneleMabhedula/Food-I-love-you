import streamlit as st
import time

st.set_page_config(
    page_title="Nerd Detector Pro",
    page_icon="🤓",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&display=swap');

        * {
            font-family: 'Space Grotesk', sans-serif;
        }

        .main {
            background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
            color: white;
        }

        .stApp {
            background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
        }

        .hero-section {
            text-align: center;
            padding: 3rem 2rem;
            background: linear-gradient(135deg, rgba(88, 43, 232, 0.2) 0%, rgba(147, 51, 234, 0.2) 100%);
            border-radius: 20px;
            margin-bottom: 3rem;
            border: 2px solid rgba(147, 51, 234, 0.3);
            box-shadow: 0 8px 32px rgba(147, 51, 234, 0.2);
        }

        .hero-title {
            font-size: 4.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 1rem;
            text-shadow: 0 0 80px rgba(147, 51, 234, 0.5);
        }

        .hero-subtitle {
            font-size: 1.5rem;
            color: #a78bfa;
            margin-bottom: 0.5rem;
            font-weight: 500;
        }

        .hero-description {
            font-size: 1.1rem;
            color: #c4b5fd;
            max-width: 600px;
            margin: 0 auto;
        }

        .question-card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 2rem;
            margin-bottom: 2rem;
            border: 1px solid rgba(147, 51, 234, 0.3);
            box-shadow: 0 4px 24px rgba(0, 0, 0, 0.2);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }

        .question-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 32px rgba(147, 51, 234, 0.3);
        }

        .question-number {
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 50px;
            font-weight: 600;
            font-size: 0.9rem;
            margin-bottom: 1rem;
        }

        .question-text {
            font-size: 1.4rem;
            font-weight: 600;
            color: #e9d5ff;
            margin-bottom: 1.5rem;
        }

        .stRadio > label {
            font-size: 1.1rem;
            color: #c4b5fd;
            font-weight: 500;
        }

        .stRadio > div {
            background: rgba(255, 255, 255, 0.03);
            padding: 1rem;
            border-radius: 10px;
        }

        .stRadio > div > label {
            background: rgba(255, 255, 255, 0.05);
            padding: 1rem 1.5rem;
            border-radius: 10px;
            margin: 0.5rem 0;
            border: 1px solid rgba(147, 51, 234, 0.2);
            transition: all 0.3s ease;
            cursor: pointer;
        }

        .stRadio > div > label:hover {
            background: rgba(147, 51, 234, 0.2);
            border-color: rgba(147, 51, 234, 0.5);
            transform: translateX(5px);
        }

        .stButton > button {
            width: 100%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            font-size: 1.3rem;
            font-weight: 600;
            padding: 1rem 2rem;
            border-radius: 50px;
            border: none;
            box-shadow: 0 8px 24px rgba(147, 51, 234, 0.4);
            transition: all 0.3s ease;
        }

        .stButton > button:hover {
            transform: translateY(-3px);
            box-shadow: 0 12px 32px rgba(147, 51, 234, 0.6);
        }

        .results-container {
            background: linear-gradient(135deg, rgba(88, 43, 232, 0.3) 0%, rgba(147, 51, 234, 0.3) 100%);
            border-radius: 20px;
            padding: 3rem;
            margin-top: 3rem;
            border: 2px solid rgba(147, 51, 234, 0.5);
            box-shadow: 0 16px 48px rgba(147, 51, 234, 0.3);
            text-align: center;
        }

        .score-display {
            font-size: 5rem;
            font-weight: 700;
            background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin: 2rem 0;
        }

        .result-title {
            font-size: 2.5rem;
            font-weight: 700;
            color: #e9d5ff;
            margin-bottom: 1rem;
        }

        .result-description {
            font-size: 1.3rem;
            color: #c4b5fd;
            line-height: 1.8;
        }

        .progress-container {
            margin: 2rem 0;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
            margin-top: 2rem;
        }

        .stat-card {
            background: rgba(255, 255, 255, 0.05);
            padding: 1.5rem;
            border-radius: 15px;
            border: 1px solid rgba(147, 51, 234, 0.3);
        }

        .stat-value {
            font-size: 2rem;
            font-weight: 700;
            color: #a78bfa;
        }

        .stat-label {
            font-size: 0.9rem;
            color: #c4b5fd;
            margin-top: 0.5rem;
        }

        .divider {
            height: 2px;
            background: linear-gradient(90deg, transparent, rgba(147, 51, 234, 0.5), transparent);
            margin: 3rem 0;
        }

        .badge {
            display: inline-block;
            padding: 0.5rem 1.5rem;
            background: rgba(147, 51, 234, 0.2);
            border: 1px solid rgba(147, 51, 234, 0.5);
            border-radius: 50px;
            color: #e9d5ff;
            font-weight: 600;
            margin: 0.5rem;
        }

        h1, h2, h3 {
            color: #e9d5ff !important;
        }

        .stMetric {
            background: rgba(255, 255, 255, 0.05);
            padding: 1.5rem;
            border-radius: 15px;
            border: 1px solid rgba(147, 51, 234, 0.3);
        }

        .stMetric label {
            color: #c4b5fd !important;
            font-size: 1.2rem !important;
        }

        .stMetric [data-testid="stMetricValue"] {
            color: #fbbf24 !important;
            font-size: 3rem !important;
            font-weight: 700 !important;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="hero-section">
        <div class="hero-title">🤓 NERD DETECTOR PRO</div>
        <div class="hero-subtitle">The Ultimate Nerdiness Assessment Tool</div>
        <div class="hero-description">
            Powered by advanced algorithms and years of nerd culture research.
            Answer 5 carefully crafted questions to discover your true nerd level.
        </div>
    </div>
""", unsafe_allow_html=True)

if 'answers' not in st.session_state:
    st.session_state.answers = {}

questions = [
    {
        "id": "q1",
        "question": "What's your ideal weekend activity?",
        "options": [
            ("Going to parties and clubs", 1, "🎉"),
            ("Watching movies at home", 2, "🎬"),
            ("Playing video games", 3, "🎮"),
            ("Reading books or comics", 4, "📚"),
            ("Building something or coding", 5, "💻")
        ]
    },
    {
        "id": "q2",
        "question": "Which movie genre speaks to your soul?",
        "options": [
            ("Romance", 1, "💕"),
            ("Action", 2, "💥"),
            ("Comedy", 3, "😂"),
            ("Sci-Fi", 4, "🚀"),
            ("Fantasy/Superhero", 5, "🦸")
        ]
    },
    {
        "id": "q3",
        "question": "How do you feel about Star Wars or Star Trek?",
        "options": [
            ("Never seen them", 1, "❓"),
            ("Heard of them", 2, "👂"),
            ("Watched a few episodes/movies", 3, "📺"),
            ("I'm a fan", 4, "⭐"),
            ("I can quote entire scenes and know the lore", 5, "🏆")
        ]
    },
    {
        "id": "q4",
        "question": "What's your dream vacation destination?",
        "options": [
            ("Beach resort", 1, "🏖️"),
            ("City sightseeing", 2, "🌆"),
            ("Adventure sports", 3, "🏔️"),
            ("Comic-Con or tech conference", 5, "🎪"),
            ("Visiting museums or historical sites", 4, "🏛️")
        ]
    },
    {
        "id": "q5",
        "question": "How many gadgets/tech devices do you own?",
        "options": [
            ("Just my phone", 1, "📱"),
            ("Phone and laptop", 2, "💻"),
            ("Phone, laptop, and tablet", 3, "📱💻"),
            ("Phone, laptop, tablet, smartwatch, and more", 4, "⌚"),
            ("I've lost count... my room is a tech lab", 5, "🔬")
        ]
    }
]

for i, q in enumerate(questions, 1):
    st.markdown(f"""
        <div class="question-card">
            <span class="question-number">Question {i} of 5</span>
            <div class="question-text">{q['question']}</div>
        </div>
    """, unsafe_allow_html=True)

    options_display = [f"{emoji} {text}" for text, score, emoji in q['options']]
    answer = st.radio(
        "",
        options_display,
        key=q['id'],
        label_visibility="collapsed"
    )

    selected_index = options_display.index(answer)
    st.session_state.answers[q['id']] = q['options'][selected_index][1]

    st.markdown("<br>", unsafe_allow_html=True)

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("🚀 CALCULATE MY NERD SCORE", type="primary"):
        with st.spinner("Analyzing your nerdiness..."):
            progress_bar = st.progress(0)
            for percent in range(100):
                time.sleep(0.01)
                progress_bar.progress(percent + 1)

            score = sum(st.session_state.answers.values())

            st.balloons()

            st.markdown('<div class="results-container">', unsafe_allow_html=True)

            st.markdown("## 🎯 YOUR RESULTS ARE IN")

            col_a, col_b, col_c = st.columns([1, 2, 1])
            with col_b:
                st.metric(label="YOUR NERD SCORE", value=f"{score} / 25")

            percentage = (score / 25) * 100
            st.progress(percentage / 100)

            st.markdown("<br>", unsafe_allow_html=True)

            if score <= 7:
                st.markdown("""
                    <div class="result-title">😎 CHILL VIBES DETECTED</div>
                    <div class="result-description">
                        You're more about the beach than the binary code. You keep it casual
                        and don't sweat the small stuff. While others debate which programming
                        language is superior, you're out living your best life. Stay cool!
                    </div>
                """, unsafe_allow_html=True)
                category = "Social Butterfly"
                recommendation = "Maybe try a sci-fi movie this weekend?"

            elif score <= 15:
                st.markdown("""
                    <div class="result-title">🧠 BALANCED NERD</div>
                    <div class="result-description">
                        You've mastered the art of balance! You can hold a conversation about
                        both sports AND superhero movies. You enjoy nerdy things but also
                        know how to have fun in the real world. Best of both worlds!
                    </div>
                """, unsafe_allow_html=True)
                category = "Well-Rounded"
                recommendation = "Perfect balance! Keep exploring new interests."

            else:
                st.markdown("""
                    <div class="result-title">🤓 CERTIFIED MEGA NERD</div>
                    <div class="result-description">
                        Welcome to the elite club! You're living your best nerdy life and we
                        absolutely love it. Your knowledge of fandoms, tech, and obscure
                        references is legendary. You probably corrected at least 3 people today.
                        Never change! 🚀
                    </div>
                """, unsafe_allow_html=True)
                category = "Elite Nerd"
                recommendation = "Have you tried building your own computer yet?"

            st.markdown("<br><br>", unsafe_allow_html=True)

            st.markdown('<div class="stats-grid">', unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value">{percentage:.0f}%</div>
                        <div class="stat-label">Nerdiness Level</div>
                    </div>
                """, unsafe_allow_html=True)

            with col2:
                st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value">{category}</div>
                        <div class="stat-label">Category</div>
                    </div>
                """, unsafe_allow_html=True)

            with col3:
                st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value">{score}</div>
                        <div class="stat-label">Points Earned</div>
                    </div>
                """, unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f"""
                <div style="text-align: center; color: #c4b5fd; font-size: 1.1rem;">
                    💡 <strong>Recommendation:</strong> {recommendation}
                </div>
            """, unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown("<br><br>", unsafe_allow_html=True)

            if st.button("🔄 Take the Test Again"):
                st.session_state.answers = {}
                st.rerun()

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

st.markdown("""
    <div style="text-align: center; color: #a78bfa; padding: 2rem;">
        <p style="font-size: 0.9rem;">Made with 💜 by nerds, for nerds</p>
        <p style="font-size: 0.8rem; color: #8b5cf6;">Nerd Detector Pro v2.0 | Accuracy: 99.9%*</p>
        <p style="font-size: 0.7rem; color: #7c3aed;">*Results may vary based on your caffeine intake</p>
    </div>
""", unsafe_allow_html=True)