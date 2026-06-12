"""Tests for YAML-backed agent team pattern definitions."""

from pathlib import Path

import pytest

from src.patterns import PATTERNS, _load_pattern_registry

EXPECTED_PATTERN_IDS = (
    "debate-critic",
    "generator-evaluator",
    "leadership",
    "planner-executor",
    "research-report",
)

EXPECTED_PATTERN_DETAILS = {
    "debate-critic": {
        "name": "Debate & Critic",
        "description": "Best-option selection via adversarial argument.",
        "flow_type": "sequential_rounds",
        "max_rounds": 3,
        "roles": [
            (
                "Proposer",
                "🗣️",
                "당신은 토론의 '찬성' 측 발언자입니다. 주어진 주제에 대해 강력한 논거를 제시하세요. 논리적 근거와 구체적 사례를 포함하세요.",
            ),
            (
                "Opponent",
                "⚔️",
                "당신은 토론의 '반대' 측 발언자입니다. 찬성 측의 약점을 파악하고 반론을 제시하세요. 비판적 사고로 논거의 허점을 드러내세요.",
            ),
            (
                "Critic",
                "🔍",
                "당신은 중립적 평가자입니다. 찬성과 반대 양측의 논거를 객관적으로 분석하세요. 각 논거의 강점과 약점을 공정하게 평가하세요.",
            ),
            (
                "Synthesizer",
                "🧩",
                "당신은 토론 종합자입니다. 양측의 논거가 수렴했는지 판단하세요. 충분히 수렴했다면 'CONVERGED'를, 아니라면 'CONTINUE'를 출력하고 이유를 설명하세요.",
            ),
            ("Scribe", "📝", "당신은 기록자입니다. 토론의 전체 내용을 체계적으로 정리하여 최종 결론 문서를 작성하세요."),
        ],
    },
    "generator-evaluator": {
        "name": "Generator & Evaluator",
        "description": "Quality-threshold artifact production via feedback loop.",
        "flow_type": "feedback_loop",
        "max_rounds": 3,
        "roles": [
            ("Generator", "🔨", "당신은 콘텐츠 생성자입니다. 주어진 주제에 대해 고품질의 초안을 작성하세요. 명확하고 구조화된 결과물을 만드세요."),
            (
                "Evaluator",
                "📊",
                "당신은 품질 평가자입니다. 제출된 결과물을 엄격하게 평가하세요. 품질이 충분하면 'PASS'를, 개선이 필요하면 'FAIL'과 함께 구체적 피드백을 제공하세요.",
            ),
            ("Refiner", "✨", "당신은 개선 전문가입니다. 평가자의 피드백을 반영하여 결과물을 개선하세요. 지적된 문제점을 모두 해결하세요."),
            ("Scribe", "📝", "당신은 기록자입니다. 전체 생성-평가 과정과 최종 결과물을 체계적으로 정리하여 문서화하세요."),
        ],
    },
    "leadership": {
        "name": "Leadership Discussion",
        "description": "Multi-domain strategic decision-making via C-level briefings.",
        "flow_type": "fan_out_sequential",
        "max_rounds": 3,
        "roles": [
            ("CEO", "👔", "당신은 CEO입니다. 전략적 의사결정을 위한 안건을 설정하고, 모든 브리핑을 종합하여 최종 결정을 내리세요."),
            ("CTO", "💻", "당신은 CTO입니다. 기술적 관점에서 주제를 분석하고 기술 전략과 실행 가능성에 대해 브리핑하세요."),
            ("CISO", "🛡️", "당신은 CISO입니다. 보안 관점에서 주제를 분석하고 위험 요소와 보안 전략에 대해 브리핑하세요."),
            ("CFO", "💰", "당신은 CFO입니다. 재무적 관점에서 주제를 분석하고 비용, ROI, 예산에 대해 브리핑하세요."),
            ("CPO", "📱", "당신은 CPO입니다. 제품 관점에서 주제를 분석하고 사용자 경험과 제품 전략에 대해 브리핑하세요."),
            ("ChiefOfStaff", "📋", "당신은 Chief of Staff입니다. 회의 전체 내용을 정리하여 회의록과 실행 항목을 문서화하세요."),
        ],
    },
    "planner-executor": {
        "name": "Planner & Executor",
        "description": "Systematic complex task execution with validation.",
        "flow_type": "sequential_tasks",
        "max_rounds": 3,
        "roles": [
            ("Planner", "📐", "당신은 계획 수립자입니다. 주어진 작업을 분석하고 단계별 실행 계획을 수립하세요. 각 단계의 수용 기준을 명확히 정의하세요."),
            ("Executor", "⚡", "당신은 실행자입니다. 계획에 따라 각 작업을 구현하세요. 수용 기준을 충족하는 결과물을 만드세요."),
            (
                "Validator",
                "✅",
                "당신은 검증자입니다. 실행 결과가 수용 기준을 충족하는지 검증하세요. 충족하면 'PASS'를, 수정이 필요하면 'REVISE'와 함께 구체적 피드백을 제공하세요.",
            ),
            ("Scribe", "📝", "당신은 기록자입니다. 계획, 실행, 검증의 전체 과정을 체계적으로 정리하여 문서화하세요."),
        ],
    },
    "research-report": {
        "name": "Research & Report",
        "description": "Trusted knowledge synthesis via research and fact-checking.",
        "flow_type": "research_loop",
        "max_rounds": 3,
        "roles": [
            ("Researcher", "🔬", "당신은 연구자입니다. 주어진 주제에 대해 깊이 있는 조사를 수행하세요. 다양한 관점과 근거를 포함하세요."),
            (
                "Reasoner",
                "🧠",
                "당신은 논리 검증자입니다. 연구 결과의 사실 관계와 논리를 검증하세요. 검증 통과 시 'PASS'를, 수정 필요 시 'REVISE'와 함께 피드백을 제공하세요.",
            ),
            ("Reporter", "📰", "당신은 리포터입니다. 검증된 연구 결과를 바탕으로 구조화된 최종 보고서를 작성하세요."),
        ],
    },
}


def test_yaml_backed_patterns_preserve_existing_values() -> None:
    """Loaded patterns preserve the existing registry order and content."""
    assert tuple(PATTERNS) == EXPECTED_PATTERN_IDS

    for pattern_id, expected in EXPECTED_PATTERN_DETAILS.items():
        pattern = PATTERNS[pattern_id]
        assert pattern.name == expected["name"]
        assert pattern.description == expected["description"]
        assert pattern.flow_type == expected["flow_type"]
        assert pattern.max_rounds == expected["max_rounds"]
        assert [(r.name, r.emoji, r.system_prompt) for r in pattern.roles] == expected["roles"]


def _write_registry(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ("patterns:\n  - id: debate-critic\n", "Invalid pattern at index 0"),
        (
            "patterns:\n"
            "  - id: debate-critic\n"
            "    name: Debate & Critic\n"
            "    description: Best-option selection via adversarial argument.\n"
            "    flow_type: sequential_rounds\n"
            "    max_rounds: 3\n"
            "    roles: []\n",
            "Invalid pattern at index 0",
        ),
        (
            "patterns:\n"
            "  - id: debate-critic\n"
            "    name: Debate & Critic\n"
            "    description: Best-option selection via adversarial argument.\n"
            "    flow_type: sequential_rounds\n"
            "    max_rounds: 3\n"
            "    roles:\n"
            "      - emoji: 🗣️\n"
            "        system_prompt: prompt\n",
            "Invalid pattern at index 0",
        ),
        ("patterns:\n  - {}\n  - {}\n", "Invalid pattern at index 0"),
    ],
)
def test_load_pattern_registry_rejects_invalid_pattern_data(
    tmp_path: Path, body: str, message: str
) -> None:
    """Invalid predefined pattern records fail before a registry is returned."""
    path = _write_registry(tmp_path / "patterns.yaml", body)

    with pytest.raises(ValueError, match=message):
        _load_pattern_registry(path)


def test_load_pattern_registry_rejects_duplicate_ids(tmp_path: Path) -> None:
    """Duplicate predefined pattern IDs fail instead of overwriting data."""
    pattern = PATTERNS["debate-critic"].model_dump()
    body = "patterns:\n"
    for _ in range(2):
        body += (
            "  - id: debate-critic\n"
            "    name: Debate & Critic\n"
            "    description: Best-option selection via adversarial argument.\n"
            "    flow_type: sequential_rounds\n"
            "    max_rounds: 3\n"
            "    roles:\n"
            f"      - name: {pattern['roles'][0]['name']}\n"
            f"        emoji: {pattern['roles'][0]['emoji']}\n"
            f"        system_prompt: {pattern['roles'][0]['system_prompt']}\n"
        )
    path = _write_registry(tmp_path / "patterns.yaml", body)

    with pytest.raises(ValueError, match="Duplicate pattern id: debate-critic"):
        _load_pattern_registry(path)
