"""
성취 시스템 CSS 스타일
"""

ACHIEVEMENT_CSS = """
    /* ============================================ */
    /* 성취 시스템 CSS 스타일                        */
    /* ============================================ */

    /* 진행률 헤더 */
    .achievement-progress-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 20px;
        padding: 1.5rem 2rem;
        margin: 1rem 0 1.5rem 0;
        color: white;
        box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
    }

    .progress-main-stats {
        display: flex;
        align-items: center;
        gap: 2rem;
        flex-wrap: wrap;
    }

    .progress-circle-container {
        flex-shrink: 0;
    }

    .progress-circle {
        width: 100px;
        height: 100px;
        border-radius: 50%;
        background: conic-gradient(
            #4CAF50 calc(var(--percent) * 1%),
            rgba(255,255,255,0.2) calc(var(--percent) * 1%)
        );
        display: flex;
        align-items: center;
        justify-content: center;
        position: relative;
    }

    .progress-circle::before {
        content: '';
        position: absolute;
        width: 80px;
        height: 80px;
        border-radius: 50%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }

    .progress-percent {
        position: relative;
        z-index: 1;
        font-size: 1.5rem;
        font-weight: bold;
    }

    .progress-details {
        flex: 1;
    }

    .progress-chapters {
        font-size: 1.2rem;
        margin-bottom: 0.5rem;
    }

    .progress-chapters .big-number {
        font-size: 2.5rem;
        font-weight: bold;
    }

    .progress-chapters .separator {
        font-size: 1.5rem;
        margin: 0 0.3rem;
        opacity: 0.7;
    }

    .progress-chapters .total-number {
        font-size: 1.5rem;
        opacity: 0.9;
    }

    .progress-chapters .label {
        font-size: 1rem;
        margin-left: 0.5rem;
        opacity: 0.8;
    }

    .progress-chars, .progress-remaining {
        font-size: 1rem;
        opacity: 0.9;
        margin: 0.3rem 0;
    }

    .streak-badge {
        display: inline-block;
        background: #FF6B6B;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        font-size: 0.9rem;
        font-weight: bold;
        margin-top: 0.5rem;
        animation: pulse-glow 2s infinite;
    }

    @keyframes pulse-glow {
        0%, 100% { box-shadow: 0 0 5px rgba(255, 107, 107, 0.5); }
        50% { box-shadow: 0 0 20px rgba(255, 107, 107, 0.8); }
    }

    .motivation-message {
        text-align: center;
        font-size: 1.3rem;
        margin-top: 1rem;
        padding-top: 1rem;
        border-top: 1px solid rgba(255,255,255,0.2);
        font-weight: 500;
    }

    /* 뱃지 팝업 */
    .badge-popup-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.7);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
        animation: fadeIn 0.3s ease;
    }

    .badge-popup {
        background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%);
        border-radius: 30px;
        padding: 3rem;
        text-align: center;
        animation: popIn 0.5s cubic-bezier(0.68, -0.55, 0.265, 1.55);
        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
    }

    .badge-popup-emoji {
        font-size: 5rem;
        animation: bounce 0.6s infinite;
    }

    .badge-popup-title {
        font-size: 1.5rem;
        color: #333;
        margin-top: 1rem;
        font-weight: bold;
    }

    .badge-popup-name {
        font-size: 2rem;
        color: #1a1a1a;
        font-weight: bold;
        margin: 0.5rem 0;
    }

    .badge-popup-desc {
        font-size: 1.2rem;
        color: #555;
    }

    /* 마일스톤 팝업 */
    .milestone-popup-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
        animation: fadeIn 0.3s ease;
    }

    .milestone-popup {
        background: linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%);
        border-radius: 30px;
        padding: 3rem 4rem;
        text-align: center;
        color: white;
        animation: popIn 0.5s cubic-bezier(0.68, -0.55, 0.265, 1.55);
        box-shadow: 0 20px 60px rgba(0,0,0,0.4);
    }

    .milestone-popup.milestone-special {
        background: linear-gradient(135deg, #FFD700 0%, #FF6B6B 50%, #4ECDC4 100%);
    }

    @keyframes rainbow-glow {
        0%, 100% { box-shadow: 0 0 30px rgba(255, 215, 0, 0.8); }
        33% { box-shadow: 0 0 30px rgba(255, 107, 107, 0.8); }
        66% { box-shadow: 0 0 30px rgba(78, 205, 196, 0.8); }
    }

    .milestone-emoji {
        font-size: 6rem;
        animation: celebrate 0.5s ease-in-out 3;
    }

    .milestone-title {
        font-size: 2.5rem;
        font-weight: bold;
        margin: 1rem 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }

    .milestone-message {
        font-size: 1.5rem;
        opacity: 0.95;
    }

    /* 뱃지 표시 섹션 */
    .badges-section {
        background: linear-gradient(135deg, #FFF8E1 0%, #FFECB3 100%);
        border-radius: 20px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 3px solid #FFB300;
    }

    .badges-section h4 {
        margin: 0 0 1rem 0;
        color: #E65100;
        font-size: 1.3rem;
    }

    .badges-container {
        display: flex;
        flex-wrap: wrap;
        gap: 0.8rem;
    }

    .badges-container.empty {
        text-align: center;
        color: #666;
        padding: 1rem;
    }

    .badge-item {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        background: white;
        padding: 0.5rem 1rem;
        border-radius: 25px;
        font-size: 1rem;
        font-weight: 600;
        box-shadow: 0 3px 10px rgba(0,0,0,0.1);
        transition: transform 0.2s;
    }

    .badge-item:hover {
        transform: scale(1.05);
    }

    .badge-item.tier-1 { border: 2px solid #81C784; }
    .badge-item.tier-2 { border: 2px solid #64B5F6; }
    .badge-item.tier-3 { border: 2px solid #BA68C8; }
    .badge-item.tier-4 { border: 2px solid #FFB74D; }
    .badge-item.tier-5 { border: 2px solid #FF8A65; }
    .badge-item.tier-6 { border: 2px solid #FFD700; background: linear-gradient(135deg, #FFF8E1, #FFD700); }

    .badge-emoji {
        font-size: 1.3rem;
    }

    /* 오늘의 목표 섹션 */
    .daily-goal-section {
        background: linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%);
        border-radius: 15px;
        padding: 1.2rem 1.5rem;
        margin: 1rem 0;
        border: 2px solid #81C784;
    }

    .daily-goal-section.achieved {
        background: linear-gradient(135deg, #C8E6C9 0%, #A5D6A7 100%);
        border-color: #4CAF50;
        animation: glow-green 2s infinite;
    }

    @keyframes glow-green {
        0%, 100% { box-shadow: 0 0 10px rgba(76, 175, 80, 0.3); }
        50% { box-shadow: 0 0 25px rgba(76, 175, 80, 0.5); }
    }

    .daily-goal-header {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 0.8rem;
    }

    .daily-goal-icon {
        font-size: 1.5rem;
    }

    .daily-goal-title {
        font-size: 1.2rem;
        font-weight: bold;
        color: #2E7D32;
    }

    .streak-indicator {
        margin-left: auto;
        background: #FF6B6B;
        color: white;
        padding: 0.2rem 0.6rem;
        border-radius: 10px;
        font-size: 0.9rem;
        font-weight: bold;
    }

    .daily-goal-bar {
        background: rgba(255,255,255,0.7);
        border-radius: 10px;
        height: 20px;
        overflow: hidden;
        margin-bottom: 0.5rem;
    }

    .daily-goal-fill {
        background: linear-gradient(90deg, #4CAF50 0%, #8BC34A 100%);
        height: 100%;
        border-radius: 10px;
        transition: width 0.5s ease;
    }

    .daily-goal-text {
        text-align: center;
        font-size: 1.1rem;
        font-weight: 600;
        color: #1B5E20;
    }

    /* 애니메이션 */
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }

    @keyframes popIn {
        from {
            opacity: 0;
            transform: scale(0.5);
        }
        to {
            opacity: 1;
            transform: scale(1);
        }
    }
"""
