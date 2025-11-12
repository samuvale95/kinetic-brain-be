import json
import math
import openai
import os
import uuid
from copy import deepcopy
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger
from sqlalchemy.orm import Session

from app.config import settings
from app.models.ai import AIResponseLog
from app.models.daily_metrics import DailyReadinessMetrics
from app.models.training_metrics import WeeklyTrainingSummary
from app.schemas.ai import (
    AIRequest,
    AIResponse,
    WorkoutAnalysisRequest,
    WorkoutAnalysisResponse,
    WorkoutPlanGenerationRequest,
)
from app.services.plan_validator import PlanValidationError, WorkoutPlanValidator
from app.services.metrics_orchestrator import enqueue_weekly_summary_job, process_metrics_jobs


class PlanGenerationError(Exception):
    """Raised when an AI workout plan chunk cannot be parsed or assembled."""

    def __init__(self, message: str, raw_chunks: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message)
        self.raw_chunks = raw_chunks or []


def _step(step_type: str, seconds: int, zone: str, notes: str, name: Optional[str] = None) -> Dict[str, Any]:
    step: Dict[str, Any] = {
        "step_type": step_type,
        "duration": {"type": "time", "seconds": seconds},
        "target": {"type": "zone", "zone": zone},
        "notes": notes,
    }
    if name:
        step["name"] = name
    return step


def _repeat(repeat: int, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "step_type": "repeat",
        "repeat": repeat,
        "steps": steps,
    }


def _segment(segment_type: str, steps: List[Dict[str, Any]], name: Optional[str] = None) -> Dict[str, Any]:
    segment: Dict[str, Any] = {"segment_type": segment_type, "steps": steps}
    if name:
        segment["name"] = name
    return segment


def _structure(
    segments: List[Dict[str, Any]],
    focus: str,
    rpe_target: Optional[int],
    description: str,
    sport: str = "run",
) -> Dict[str, Any]:
    return {
        "sport": sport,
        "segments": segments,
        "metadata": {
            "focus": focus,
            "rpe_target": rpe_target,
            "description": description,
        },
    }


RAW_MOCK_PLAN: List[Dict[str, Any]] = [
    {
        "week": 1,
        "focus": "Base building",
        "workouts": [
            {
                "day": "Monday",
                "type": "Endurance",
                "sport": "run",
                "duration_minutes": 45,
                "intensity": "Z2",
                "rpe_target": 3,
                "zone": "Z2",
                "description": "Steady run focusing on building aerobic capacity.",
                "modifications": "If experiencing any discomfort, reduce pace or shorten the duration.",
                "structure": _structure(
                    [
                        _segment("warmup", [_step("steady", 600, "Z1", "Easy jog to loosen up")], "Warm-up"),
                        _segment(
                            "main",
                            [_step("steady", 2100, "Z2", "Maintain a comfortable pace where conversation is possible")],
                            "Main Set",
                        ),
                        _segment("cooldown", [_step("steady", 600, "Z1", "Cool down with an easy jog")], "Cool-down"),
                    ],
                    "Base building",
                    3,
                    "Maintain a steady, comfortable pace to build endurance.",
                ),
            },
            {
                "day": "Wednesday",
                "type": "Speed",
                "sport": "run",
                "duration_minutes": 30,
                "intensity": "Z4",
                "rpe_target": 7,
                "zone": "Z4",
                "description": "Short intervals to improve speed and cardiac efficiency.",
                "modifications": "Adjust the number of intervals based on fatigue levels.",
                "structure": _structure(
                    [
                        _segment("warmup", [_step("steady", 600, "Z2", "Gradually increase your heart rate")], "Warm-up"),
                        _segment(
                            "main",
                            [
                                _repeat(
                                    4,
                                    [
                                        _step("interval", 60, "Z4", "Run at a fast pace, close to race effort"),
                                        _step("recovery", 180, "Z1", "Walk or jog for recovery"),
                                    ],
                                )
                            ],
                            "Intervals",
                        ),
                        _segment("cooldown", [_step("steady", 600, "Z1", "Ease out of the session with a gentle jog")], "Cool-down"),
                    ],
                    "Speed development",
                    7,
                    "Intense intervals to boost speed and improve recovery.",
                ),
            },
            {
                "day": "Friday",
                "type": "Recovery",
                "sport": "run",
                "duration_minutes": 30,
                "intensity": "Z1",
                "rpe_target": 2,
                "zone": "Z1",
                "description": "Easy recovery run to promote muscle repair and mitigate fatigue.",
                "modifications": "If feeling overly fatigued, consider a brisk walk instead of a run.",
                "structure": _structure(
                    [
                        _segment("warmup", [_step("steady", 300, "Z1", "Start with a gentle jog")], "Warm-up"),
                        _segment("main", [_step("steady", 1200, "Z1", "Maintain a light, easy pace to facilitate recovery")], "Recovery Run"),
                        _segment("cooldown", [_step("steady", 300, "Z1", "Finish with walking or very easy jogging")], "Cool-down"),
                    ],
                    "Recovery",
                    2,
                    "Keep effort very easy to promote recovery.",
                ),
            },
            {
                "day": "Sunday",
                "type": "Long Run",
                "sport": "run",
                "duration_minutes": 75,
                "intensity": "Z3",
                "rpe_target": 5,
                "zone": "Z3",
                "description": "Longer duration run to enhance aerobic endurance.",
                "modifications": "Hydrate well and adjust pace to maintain consistency.",
                "structure": _structure(
                    [
                        _segment("warmup", [_step("steady", 900, "Z2", "Start gently to prepare for a longer effort")], "Warm-up"),
                        _segment(
                            "main",
                            [_step("steady", 3600, "Z3", "Maintain a steady, challenging pace with controlled breathing")],
                            "Main Set",
                        ),
                        _segment("cooldown", [_step("steady", 900, "Z1", "Gradually reduce pace to cool down")], "Cool-down"),
                    ],
                    "Aerobic endurance",
                    5,
                    "Build endurance and practice pacing over longer efforts.",
                ),
            },
        ],
    },
    {
        "week": 2,
        "focus": "Base building and speed introduction",
        "workouts": [
            {
                "day": "Monday",
                "type": "Endurance",
                "sport": "run",
                "duration_minutes": 60,
                "intensity": "Z2",
                "rpe_target": 3,
                "zone": "Z2",
                "description": "Steady state run to further build the aerobic base.",
                "structure": _structure(
                    [
                        _segment("warmup", [_step("steady", 900, "Z1", "Easy jog to warm up")], "Warm-up"),
                        _segment("main", [_step("steady", 3600, "Z2", "Maintain a steady moderate pace")], "Main Set"),
                        _segment("cooldown", [_step("steady", 600, "Z1", "Cool down with an easy jog")], "Cool-down"),
                    ],
                    "Base building",
                    3,
                    "Focus on maintaining a relaxed, steady effort.",
                ),
            },
            {
                "day": "Wednesday",
                "type": "Speed",
                "sport": "run",
                "duration_minutes": 50,
                "intensity": "Z4",
                "rpe_target": 7,
                "zone": "Z4",
                "description": "More intense interval training to enhance speed.",
                "structure": _structure(
                    [
                        _segment("warmup", [_step("steady", 900, "Z2", "Gradual warm-up")], "Warm-up"),
                        _segment(
                            "main",
                            [
                                _repeat(
                                    6,
                                    [
                                        _step("interval", 180, "Z4", "Push to high intensity"),
                                        _step("recovery", 180, "Z1", "Recovery jog"),
                                    ],
                                )
                            ],
                            "Speed Intervals",
                        ),
                        _segment("cooldown", [_step("steady", 600, "Z1", "Cool down with easy jogging")], "Cool-down"),
                    ],
                    "Speed development",
                    7,
                    "Enhance top-end speed with repeat intervals.",
                ),
            },
            {
                "day": "Friday",
                "type": "Long Run",
                "sport": "run",
                "duration_minutes": 90,
                "intensity": "Z2",
                "rpe_target": 4,
                "zone": "Z2",
                "description": "Extended duration run to reinforce endurance.",
                "structure": _structure(
                    [
                        _segment("warmup", [_step("steady", 900, "Z1", "Start gently")], "Warm-up"),
                        _segment("main", [_step("steady", 6600, "Z2", "Maintain a consistent, moderate pace")], "Main Set"),
                        _segment("cooldown", [_step("steady", 900, "Z1", "Ease out of the effort")], "Cool-down"),
                    ],
                    "Endurance",
                    4,
                    "Build stamina with a longer steady-state run.",
                ),
            },
            {
                "day": "Sunday",
                "type": "Recovery Run",
                "sport": "run",
                "duration_minutes": 45,
                "intensity": "Z1",
                "rpe_target": 2,
                "zone": "Z1",
                "description": "Easy run to promote recovery.",
                "modifications": "Extend cooldown if feeling particularly fatigued.",
                "structure": _structure(
                    [
                        _segment("warmup", [_step("steady", 300, "Z1", "Begin with a gentle jog")], "Warm-up"),
                        _segment("main", [_step("steady", 2100, "Z1", "Keep a relaxed, comfortable pace")], "Recovery Run"),
                        _segment("cooldown", [_step("steady", 300, "Z1", "Cool down with walking or light jogging")], "Cool-down"),
                    ],
                    "Recovery",
                    2,
                    "Allow muscles to recover before the next block.",
                ),
            },
        ],
    },
    {
        "week": 3,
        "focus": "VO2 Max and Speed Endurance",
        "workouts": [
            {
                "day": "Monday",
                "type": "VO2 Max Intervals",
                "sport": "run",
                "duration_minutes": 50,
                "intensity": "Z5",
                "rpe_target": 8,
                "zone": "Z5",
                "description": "High-intensity interval training to boost VO2 max.",
                "modifications": "Reduce the number of intervals if unable to sustain intensity.",
                "structure": _structure(
                    [
                        _segment("warmup", [_step("steady", 900, "Z2", "Gradual warm-up to prepare muscles")], "Warm-up"),
                        _segment(
                            "main",
                            [
                                _repeat(
                                    6,
                                    [
                                        _step("interval", 180, "Z5", "Maintain high intensity for VO2 max gains."),
                                        _step("recovery", 240, "Z2", "Active recovery at a lower intensity."),
                                    ],
                                )
                            ],
                            "High-Intensity Intervals",
                        ),
                        _segment("cooldown", [_step("steady", 900, "Z1", "Cool down to ensure proper recovery.")], "Cool-down"),
                    ],
                    "VO2 Max enhancement",
                    8,
                    "Intense intervals to increase aerobic capacity.",
                ),
            },
            {
                "day": "Wednesday",
                "type": "Tempo Run",
                "sport": "run",
                "duration_minutes": 40,
                "intensity": "Z4",
                "rpe_target": 7,
                "zone": "Z4",
                "description": "Sustained effort run to build speed endurance.",
                "modifications": "Adjust the tempo duration based on fatigue levels.",
                "structure": _structure(
                    [
                        _segment("warmup", [_step("steady", 600, "Z2", "Easy jog to prepare for tempo pace.")], "Warm-up"),
                        _segment("main", [_step("steady", 1800, "Z4", "Hold a challenging but sustainable pace.")], "Tempo Pace"),
                        _segment("cooldown", [_step("steady", 600, "Z1", "Complete the session with a gradual cooldown.")], "Cool-down"),
                    ],
                    "Speed endurance",
                    7,
                    "Continuous effort at a controlled, hard pace.",
                ),
            },
            {
                "day": "Friday",
                "type": "Easy Run",
                "sport": "run",
                "duration_minutes": 45,
                "intensity": "Z2",
                "rpe_target": 4,
                "zone": "Z2",
                "description": "Recovery run at a comfortable pace.",
                "structure": _structure(
                    [
                        _segment("warmup", [_step("steady", 600, "Z1", "Easy jogging to start.")], "Warm-up"),
                        _segment("main", [_step("steady", 2100, "Z2", "Maintain a relaxed, comfortable pace.")], "Steady Run"),
                        _segment("cooldown", [_step("steady", 600, "Z1", "Cool down to promote recovery.")], "Cool-down"),
                    ],
                    "Recovery",
                    4,
                    "Low intensity to aid in muscle recovery.",
                ),
            },
            {
                "day": "Sunday",
                "type": "Long Run",
                "sport": "run",
                "duration_minutes": 90,
                "intensity": "Z3",
                "rpe_target": 6,
                "zone": "Z3",
                "description": "Extended duration run to build endurance.",
                "modifications": "Adjust pace based on physical response to previous workouts.",
                "structure": _structure(
                    [
                        _segment("warmup", [_step("steady", 900, "Z2", "Easy jog to begin.")], "Warm-up"),
                        _segment("main", [_step("steady", 4200, "Z3", "Maintain a steady, moderate pace throughout.")], "Extended Steady Run"),
                        _segment("cooldown", [_step("steady", 900, "Z1", "Cool down to end the session.")], "Cool-down"),
                    ],
                    "Endurance",
                    6,
                    "Maintain a steady pace for the duration.",
                ),
            },
        ],
    },
    {
        "week": 4,
        "focus": "Recovery and Technique",
        "workouts": [
            {
                "day": "Monday",
                "type": "Recovery Run",
                "sport": "run",
                "duration_minutes": 40,
                "intensity": "Z1",
                "rpe_target": 3,
                "zone": "Z1",
                "description": "Light recovery run to enhance blood flow and aid recovery.",
                "structure": _structure(
                    [
                        _segment("warmup", [_step("steady", 600, "Z1", "Easy starting pace")], "Warm-up"),
                        _segment("main", [_step("steady", 1800, "Z1", "Maintain a comfortable, easy pace")], "Main Set"),
                        _segment("cooldown", [_step("steady", 600, "Z1", "Cool down at a very easy pace")], "Cool-down"),
                    ],
                    "Recovery",
                    3,
                    "Ensure relaxed breathing and focus on recovery.",
                ),
            },
            {
                "day": "Wednesday",
                "type": "Technique Run",
                "sport": "run",
                "duration_minutes": 50,
                "intensity": "Z2",
                "rpe_target": 4,
                "zone": "Z2",
                "description": "Focus on running form and technique over a moderate distance.",
                "structure": _structure(
                    [
                        _segment("warmup", [_step("steady", 600, "Z1", "Gradually increase pace")], "Warm-up"),
                        _segment("main", [_step("steady", 2400, "Z2", "Focus on maintaining proper running form")], "Main Set"),
                        _segment("cooldown", [_step("steady", 600, "Z1", "Slow down and relax")], "Cool-down"),
                    ],
                    "Technique",
                    4,
                    "Concentrate on stride efficiency and posture.",
                ),
            },
            {
                "day": "Friday",
                "type": "Active Recovery",
                "sport": "run",
                "duration_minutes": 30,
                "intensity": "Z1",
                "rpe_target": 2,
                "zone": "Z1",
                "description": "Very light jog or walk to keep legs active without adding stress.",
                "structure": _structure(
                    [
                        _segment("warmup", [_step("steady", 300, "Z1", "Start very easy")], "Warm-up"),
                        _segment("main", [_step("steady", 1500, "Z1", "Maintain a very gentle pace")], "Main Set"),
                        _segment("cooldown", [_step("steady", 300, "Z1", "Cool down slowly")], "Cool-down"),
                    ],
                    "Recovery",
                    2,
                    "Maintain light movement to promote recovery.",
                ),
            },
            {
                "day": "Sunday",
                "type": "Long Run",
                "sport": "run",
                "duration_minutes": 90,
                "intensity": "Z2",
                "rpe_target": 5,
                "zone": "Z2",
                "description": "Longer duration run at a controlled pace to build endurance.",
                "structure": _structure(
                    [
                        _segment("warmup", [_step("steady", 900, "Z1", "Gradually build up to Z2")], "Warm-up"),
                        _segment("main", [_step("steady", 4200, "Z2", "Maintain a steady, controlled pace")], "Main Set"),
                        _segment("cooldown", [_step("steady", 900, "Z1", "Cool down at an easy pace")], "Cool-down"),
                    ],
                    "Endurance",
                    5,
                    "Focus on maintaining a steady pace for the duration.",
                ),
            },
        ],
    },
    {
        "week": 5,
        "focus": "Threshold and Race Pace",
        "workouts": [
            {
                "day": "Monday",
                "type": "Threshold Intervals",
                "sport": "run",
                "duration_minutes": 50,
                "intensity": "Z4",
                "rpe_target": 8,
                "zone": "Z4",
                "description": "Structured threshold intervals to enhance race pace endurance.",
                "structure": _structure(
                    [
                        _segment("warmup", [_step("steady", 900, "Z2", "Easy jog to prepare muscles")], "Warm-up"),
                        _segment(
                            "main",
                            [
                                _repeat(
                                    4,
                                    [
                                        _step("interval", 300, "Z4", "Maintain threshold pace"),
                                        _step("recovery", 180, "Z2", "Active recovery jog"),
                                    ],
                                )
                            ],
                            "Main Set",
                        ),
                        _segment("cooldown", [_step("steady", 600, "Z1", "Cool down to aid recovery")], "Cool-down"),
                    ],
                    "Building race pace efficiency",
                    8,
                    "Focus on maintaining form and efficiency at threshold pace.",
                ),
            },
            {
                "day": "Wednesday",
                "type": "Tempo Run",
                "sport": "run",
                "duration_minutes": 45,
                "intensity": "Z3",
                "rpe_target": 7,
                "zone": "Z3",
                "description": "Continuous tempo run.",
                "structure": _structure(
                    [
                        _segment("warmup", [_step("steady", 600, "Z2", "Gradual warm-up")], "Warm-up"),
                        _segment("main", [_step("steady", 1800, "Z3", "Sustain a steady tempo pace")], "Main Set"),
                        _segment("cooldown", [_step("steady", 600, "Z1", "Ease down to promote recovery")], "Cool-down"),
                    ],
                    "Improving metabolic efficiency",
                    7,
                    "Maintain a consistent effort throughout the tempo run.",
                ),
            },
            {
                "day": "Friday",
                "type": "Easy Run",
                "sport": "run",
                "duration_minutes": 30,
                "intensity": "Z2",
                "rpe_target": 4,
                "zone": "Z2",
                "description": "Recovery easy run to maintain weekly mileage.",
                "structure": _structure(
                    [
                        _segment("warmup", [_step("steady", 300, "Z1", "Gentle warm-up")], "Warm-up"),
                        _segment("main", [_step("steady", 1500, "Z2", "Maintain an easy, conversational pace")], "Main Set"),
                        _segment("cooldown", [_step("steady", 300, "Z1", "Cool down at an easy pace")], "Cool-down"),
                    ],
                    "Active recovery",
                    4,
                    "Keep the pace easy and comfortable.",
                ),
            },
            {
                "day": "Sunday",
                "type": "Long Run",
                "sport": "run",
                "duration_minutes": 90,
                "intensity": "Z2",
                "rpe_target": 6,
                "zone": "Z2",
                "description": "Long endurance run to build aerobic capacity.",
                "structure": _structure(
                    [
                        _segment("warmup", [_step("steady", 600, "Z2", "Start gently to prepare for the effort")], "Warm-up"),
                        _segment("main", [_step("steady", 4200, "Z2", "Maintain a steady, sustainable pace")], "Main Set"),
                        _segment("cooldown", [_step("steady", 600, "Z1", "Cool down to enhance recovery")], "Cool-down"),
                    ],
                    "Aerobic endurance",
                    6,
                    "Focus on maintaining a consistent pace that allows for conversation.",
                ),
            },
        ],
    },
    {
        "week": 6,
        "focus": "High-Intensity Intervals and Long Run",
        "workouts": [
            {
                "day": "Monday",
                "type": "Intervals",
                "sport": "run",
                "duration_minutes": 55,
                "intensity": "Mixed",
                "rpe_target": 8,
                "zone": "Z5",
                "description": "Speed intervals to sharpen top-end speed.",
                "structure": _structure(
                    [
                        _segment("warmup", [_step("steady", 900, "Z1", "Easy jog to prepare muscles for intense work")], "Warm-up"),
                        _segment(
                            "main",
                            [
                                _repeat(
                                    8,
                                    [
                                        _step("interval", 60, "Z5", "Run at high intensity."),
                                        _step("recovery", 120, "Z2", "Recovery jog."),
                                    ],
                                )
                            ],
                            "Speed Intervals",
                        ),
                        _segment("cooldown", [_step("steady", 900, "Z1", "Cool down to aid recovery")], "Cool-down"),
                    ],
                    "Improving speed and recovery",
                    8,
                    "Focus on fast recovery during the short rest intervals.",
                ),
            },
            {
                "day": "Wednesday",
                "type": "Tempo Run",
                "sport": "run",
                "duration_minutes": 40,
                "intensity": "Z4",
                "rpe_target": 7,
                "zone": "Z4",
                "description": "Maintain a steady, hard pace.",
                "structure": _structure(
                    [
                        _segment("warmup", [_step("steady", 600, "Z1", "Warm-up at an easy pace")], "Warm-up"),
                        _segment("main", [_step("steady", 1800, "Z4", "Run at a challenging but sustainable pace")], "Tempo"),
                        _segment("cooldown", [_step("steady", 600, "Z1", "Cool down to aid recovery")], "Cool-down"),
                    ],
                    "Building endurance at a higher pace",
                    7,
                    "Focus on maintaining a consistent effort.",
                ),
            },
            {
                "day": "Friday",
                "type": "Easy Run",
                "sport": "run",
                "duration_minutes": 30,
                "intensity": "Z2",
                "rpe_target": 4,
                "zone": "Z2",
                "description": "Recovery run at a relaxed pace.",
                "structure": _structure(
                    [
                        _segment("warmup", [_step("steady", 300, "Z1", "Gentle jog to start")], "Warm-up"),
                        _segment("main", [_step("steady", 1500, "Z2", "Maintain an easy, comfortable pace")], "Easy pace"),
                        _segment("cooldown", [_step("steady", 300, "Z1", "Cool down")], "Cool-down"),
                    ],
                    "Active recovery",
                    4,
                    "Focus on relaxation and enjoying the run.",
                ),
            },
            {
                "day": "Sunday",
                "type": "Long Run",
                "sport": "run",
                "duration_minutes": 90,
                "intensity": "Z3",
                "rpe_target": 6,
                "zone": "Z3",
                "description": "Long endurance run to build stamina.",
                "structure": _structure(
                    [
                        _segment("warmup", [_step("steady", 900, "Z1", "Start with an easy jog")], "Warm-up"),
                        _segment("main", [_step("steady", 4200, "Z3", "Maintain a steady, moderate pace")], "Endurance"),
                        _segment("cooldown", [_step("steady", 900, "Z1", "Gradually cool down")], "Cool-down"),
                    ],
                    "Building aerobic base and endurance",
                    6,
                    "Focus on maintaining a consistent pace and form.",
                ),
            },
        ],
    },
    {
        "week": 7,
        "focus": "Taper and Race Preparation",
        "workouts": [
            {
                "day": "Monday",
                "type": "Recovery Run",
                "sport": "run",
                "duration_minutes": 30,
                "intensity": "Z1",
                "rpe_target": 3,
                "zone": "Z1",
                "description": "Light recovery run to maintain leg turnover without adding fatigue.",
                "structure": _structure(
                    [
                        _segment("warmup", [_step("steady", 600, "Z1", "Easy jog to loosen up the muscles")], "Warm-up"),
                        _segment("main", [_step("steady", 1200, "Z1", "Maintain a relaxed pace, focus on smooth breathing")], "Main Set"),
                        _segment("cooldown", [_step("steady", 300, "Z1", "Slow down to a very easy jog or walk")], "Cool-down"),
                    ],
                    "Recovery",
                    3,
                    "Keep the effort light while maintaining leg turnover.",
                ),
            },
            {
                "day": "Wednesday",
                "type": "Pre-Race Workout",
                "sport": "run",
                "duration_minutes": 50,
                "intensity": "Z3",
                "rpe_target": 6,
                "zone": "Z3",
                "description": "Shorter intervals to sharpen race pace feeling.",
                "structure": _structure(
                    [
                        _segment("warmup", [_step("steady", 900, "Z1", "Gradually increase pace towards the end of warm-up")], "Warm-up"),
                        _segment(
                            "main",
                            [
                                _repeat(
                                    5,
                                    [
                                        _step("interval", 180, "Z3", "Run at goal race pace"),
                                        _step("recovery", 180, "Z1", "Easy jog for recovery"),
                                    ],
                                )
                            ],
                            "Intervals",
                        ),
                        _segment("cooldown", [_step("steady", 600, "Z1", "Cool down with an easy jog or walk")], "Cool-down"),
                    ],
                    "Race readiness",
                    6,
                    "Sharpen race pace mechanics while keeping overall load light.",
                ),
            },
            {
                "day": "Friday",
                "type": "Easy Run",
                "sport": "run",
                "duration_minutes": 30,
                "intensity": "Z2",
                "rpe_target": 4,
                "zone": "Z2",
                "description": "Easy run to keep the legs moving pre-race.",
                "structure": _structure(
                    [
                        _segment("warmup", [_step("steady", 600, "Z1", "Light jog to start")], "Warm-up"),
                        _segment("main", [_step("steady", 1200, "Z2", "Keep a comfortable pace, focus on relaxation")], "Main Set"),
                        _segment("cooldown", [_step("steady", 300, "Z1", "Ease into a walk or slow jog")], "Cool-down"),
                    ],
                    "Taper",
                    4,
                    "Maintain movement without generating fatigue.",
                ),
            },
            {
                "day": "Sunday",
                "type": "Race Day",
                "sport": "run",
                "duration_minutes": 120,
                "intensity": "Race Pace",
                "rpe_target": 9,
                "zone": "Z4",
                "description": "Execute race plan as practiced. Focus on pacing and maintaining effort through the finish.",
                "modifications": "Follow the race plan, hydrate well, and adjust to conditions.",
                "structure": _structure(
                    [
                        _segment("warmup", [_step("steady", 900, "Z1", "Light jog with a few strides to prepare for race")], "Pre-Race Warm-up"),
                        _segment("main", [_step("steady", 5400, "Z4", "Maintain target race pace and adjust as needed.")], "Race"),
                        _segment("cooldown", [_step("steady", 600, "Z1", "Cool down gradually to aid recovery")], "Post-Race Cool-down"),
                    ],
                    "Race execution",
                    9,
                    "Execute everything trained for and manage effort across the race distance.",
                ),
            },
        ],
    },
]


def _build_mock_running_plan_standard() -> Dict[str, Any]:
    return {
        "title": "7-Week Intermediate Running Plan for Race Preparation",
        "description": (
            "Plan designed to build endurance, introduce speed work, and prepare for a race. "
            "Includes structured warm-up, main sets, and cool-down for every workout."
        ),
        "sport_type": "running",
        "level": "intermediate",
        "goal": "Gara",
        "duration_weeks": 7,
        "weekly_hours": None,
        "weeks": RAW_MOCK_PLAN,
    }


MOCK_RUNNING_PLAN_STANDARD: Dict[str, Any] = _build_mock_running_plan_standard()


def _truncate_text(value: Optional[str], limit: int = 500) -> Optional[str]:
    if not value:
        return None
    if len(value) <= limit:
        return value
    return f"{value[:limit]}...<truncated>"


class AIService:
    def __init__(self, db: Optional[Session] = None):
        self.db = db
        openai.api_key = settings.openai_api_key
        self.client = openai.OpenAI(api_key=settings.openai_api_key)
        self.mock_mode = settings.mock_llm
        self.plan_validator = WorkoutPlanValidator()
    
    def generate_response(self, request: AIRequest) -> AIResponse:
        """Generate AI response using OpenAI API"""
        request_id = str(uuid.uuid4())
        resolved_max_tokens = request.max_tokens or settings.openai_max_tokens
        resolved_temperature = request.temperature or 0.7

        log_ctx: Dict[str, Any] = {
            "ai_request_id": request_id,
            "model": settings.openai_model,
            "prompt_length": len(request.prompt),
            "has_context": request.context is not None,
            "response_format": request.response_format.get("type") if request.response_format else None,
            "max_tokens": resolved_max_tokens,
            "temperature": resolved_temperature,
        }

        prompt_preview = _truncate_text(request.prompt, limit=400)
        if prompt_preview:
            log_ctx["prompt_preview"] = prompt_preview

        if request.context:
            if isinstance(request.context, dict):
                log_ctx["context_keys"] = list(request.context.keys())
            else:
                log_ctx["context_type"] = type(request.context).__name__

        logger.bind(**log_ctx).info("[AI] Starting OpenAI API call")
        
        try:
            request_kwargs = dict(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": "You are a professional sports coach and training expert specialized in running, triathlon, cycling, swimming, and trail. You create detailed, scientifically based training plans tailored to athlete level, goals, and time availability. When personal data is unavailable, provide generic yet effective plans. Always structure plans with clear workout types, intensities, progressions, rest days, and phases. Respect privacy preferences and adapt your responses accordingly."},
                    {"role": "user", "content": request.prompt}
                ],
                max_tokens=request.max_tokens or settings.openai_max_tokens,
                temperature=request.temperature or 0.7,
            )

            if request.response_format:
                request_kwargs["response_format"] = request.response_format

            response = self.client.chat.completions.create(**request_kwargs)
            
            # Log response details
            response_content = response.choices[0].message.content
            usage_info = response.usage.dict() if response.usage else None

            response_context = {
                **log_ctx,
                "model": response.model,
                "response_length": len(response_content),
                "response_preview": _truncate_text(response_content, limit=400),
                "usage": usage_info,
            }

            logger.bind(**response_context).info("[AI] OpenAI API call successful")
            
            ai_response = AIResponse(
                response=response_content,
                usage=usage_info,
                model=response.model,
                created_at=datetime.utcnow().isoformat()
            )
            
            return ai_response
            
        except Exception as e:
            error_context = {**log_ctx, "error": str(e)}
            logger.bind(**error_context).exception("[AI] OpenAI API call failed")
            raise Exception(f"AI service error: {str(e)}")
    
    def generate_workout_plan(
        self,
        request: WorkoutPlanGenerationRequest,
        *,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Generate a personalized workout plan using AI"""
        logger.info(f"[WORKOUT_PLAN] Starting workout plan generation - sport: {request.sport_type}, level: {request.level}, goal: {request.goal}")
        logger.debug(f"[WORKOUT_PLAN] Request details: sport_type={request.sport_type}, level={request.level}, duration_weeks={request.duration_weeks}, weekly_hours={request.weekly_hours}, has_user_profile={request.user_profile is not None}, has_preferences={request.preferences is not None}, start_date={request.start_date}, target_date={request.target_date}")

        request_data = {
            "sport_type": request.sport_type,
            "level": request.level,
            "goal": request.goal,
            "duration_weeks": request.duration_weeks,
            "start_date": request.start_date,
            "target_date": request.target_date,
            "weekly_hours": request.weekly_hours,
            "user_profile": request.user_profile,
            "preferences": request.preferences,
            "race_distance_km": request.race_distance_km,
            "race_type": request.race_type,
        }

        try:
            total_weeks = self._resolve_plan_duration(request)
        except ValueError as exc:
            logger.error(f"[WORKOUT_PLAN] Unable to determine plan duration: {exc}")
            raise

        # Update request object/state with resolved duration for downstream usage
        request.duration_weeks = total_weeks
        request_data["resolved_duration_weeks"] = total_weeks

        logger.info(f"[WORKOUT_PLAN] Resolved plan duration: {total_weeks} weeks")
        logger.info(f"[WORKOUT_PLAN] Full request data: {json.dumps(request_data, indent=2, default=str)}")

        if self.mock_mode:
            logger.info(f"[WORKOUT_PLAN] Using MOCK mode for plan generation")
            prompt = self._build_workout_plan_prompt(
                request,
                duration_weeks=total_weeks,
                week_start=1,
                week_end=total_weeks,
                previous_weeks_summary=None,
            )
            logger.info(f"[WORKOUT_PLAN][MOCK] Building same prompt as real LLM to validate data flow")
            logger.debug(f"[WORKOUT_PLAN][MOCK] Prompt that would be sent to LLM: {prompt[:1000]}...")

            ai_request = AIRequest(
                prompt=prompt,
                context=request.user_profile,
                max_tokens=3500,
                temperature=0.7,
                response_format={"type": "json_schema", "json_schema": WORKOUT_PLAN_JSON_SCHEMA},
            )
            logger.info(f"[WORKOUT_PLAN][MOCK] AIRequest created - prompt_length: {len(ai_request.prompt)}, has_context: {ai_request.context is not None}, max_tokens: {ai_request.max_tokens}")

            result = self._generate_mock_workout_plan(request, prompt, ai_request)
            result["duration_weeks"] = total_weeks
            logger.info(f"[WORKOUT_PLAN][MOCK] Mock plan generated successfully - title: {result.get('title', 'N/A')}")
            logger.debug(f"[WORKOUT_PLAN][MOCK] Mock plan keys: {list(result.keys())}")
            return result

        raw_chunks: List[Dict[str, Any]] = []
        parse_success = False
        error_message: Optional[str] = None

        try:
            plan_metadata, combined_weeks, raw_chunks = self._generate_plan_batches(
                request=request,
                total_weeks=total_weeks,
                user_id=user_id,
                base_request_payload=request_data,
            )

            plan_data = self._assemble_plan_data(
                request=request,
                total_weeks=total_weeks,
                plan_metadata=plan_metadata,
                weeks=combined_weeks,
            )

            logger.info(f"[WORKOUT_PLAN] Successfully assembled plan with {len(combined_weeks)} weeks across {len(raw_chunks)} chunk(s)")
            parse_success = True

            user_state = self._build_user_state(user_id)
            self.plan_validator.validate(plan_data, user_state=user_state)

            if self.db and user_id:
                try:
                    plan_start = plan_data.get("start_date")
                    if plan_start:
                        week_start = datetime.strptime(plan_start, "%Y-%m-%d").date()
                    else:
                        week_start = datetime.utcnow().date()
                    week_start = week_start - timedelta(days=week_start.weekday())
                    enqueue_weekly_summary_job(self.db, user_id=user_id, week_start=week_start)
                    process_metrics_jobs(self.db, limit=1)
                except Exception as exc:
                    logger.warning(
                        "[WORKOUT_PLAN] Failed to enqueue/process weekly summary after plan generation for user=%s: %s",
                        user_id,
                        exc,
                    )
        except PlanGenerationError as exc:
            error_message = str(exc)
            logger.warning(f"[WORKOUT_PLAN] {error_message} - falling back to text response")
            if exc.raw_chunks:
                raw_chunks = exc.raw_chunks
            plan_data = self._build_fallback_plan(request, total_weeks, raw_chunks)
        except PlanValidationError as exc:
            error_message = f"Plan validation failed: {', '.join(exc.violations)}"
            logger.error(f"[WORKOUT_PLAN] {error_message}")
            parse_success = False
            raise PlanGenerationError(error_message, raw_chunks=raw_chunks) from exc
        finally:
            combined_prompt = self._combine_prompts(raw_chunks)
            combined_response = self._combine_raw_chunks(raw_chunks)

            self._log_ai_response(
                request_type="workout_plan",
                user_id=user_id,
                prompt=combined_prompt,
                request_payload={**request_data, "chunk_count": len(raw_chunks)},
                response_text=combined_response,
                model=(raw_chunks[-1]["model"] if raw_chunks else None),
                parse_success=parse_success,
                error_message=error_message,
            )

        return plan_data
    
    def _generate_plan_batches(
        self,
        *,
        request: WorkoutPlanGenerationRequest,
        total_weeks: int,
        user_id: Optional[int],
        base_request_payload: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Call the LLM in chunks and merge their responses."""
        sport = (request.sport_type or "").lower()
        if sport in {"running", "run", "trail", "trail running"}:
            chunk_size = 2
        elif sport in {"triathlon"}:
            chunk_size = 1
        elif sport in {"cycling", "bike"}:
            chunk_size = 2
        else:
            chunk_size = 1
        week_ranges = self._build_week_ranges(total_weeks, chunk_size=chunk_size)
        logger.info(f"[WORKOUT_PLAN] Generating plan in {len(week_ranges)} chunk(s) of up to {chunk_size} weeks")

        combined_weeks: List[Dict[str, Any]] = []
        plan_metadata: Dict[str, Any] = {}
        raw_chunks: List[Dict[str, Any]] = []
        previous_summary: Optional[str] = None

        for index, (week_start, week_end) in enumerate(week_ranges, start=1):
            prompt = self._build_workout_plan_prompt(
                request,
                duration_weeks=total_weeks,
                week_start=week_start,
                week_end=week_end,
                previous_weeks_summary=previous_summary,
            )
            logger.debug(f"[WORKOUT_PLAN][CHUNK {index}] Prompt length: {len(prompt)} characters")
            logger.debug(f"[WORKOUT_PLAN][CHUNK {index}] Prompt preview: {prompt[:600]}...")

            ai_request = AIRequest(
                prompt=prompt,
                context=request.user_profile,
                max_tokens=3500,
                temperature=0.7,
                response_format={"type": "json_schema", "json_schema": WORKOUT_PLAN_JSON_SCHEMA},
            )

            response = self.generate_response(ai_request)
            response_text = response.response

            chunk_payload = {
                **base_request_payload,
                "chunk_index": index,
                "chunk_week_start": week_start,
                "chunk_week_end": week_end,
                "resolved_duration_weeks": total_weeks,
            }

            raw_chunks.append(
                {
                    "index": index,
                    "week_start": week_start,
                    "week_end": week_end,
                    "prompt": prompt,
                    "response": response_text,
                    "model": response.model,
                }
            )

            try:
                partial_plan = json.loads(response_text)
            except json.JSONDecodeError as exc:
                logger.warning(f"[WORKOUT_PLAN][CHUNK {index}] JSON parsing failed: {exc}")
                self._log_ai_response(
                    request_type=f"workout_plan_chunk_{index}",
                    user_id=user_id,
                    prompt=prompt,
                    request_payload=chunk_payload,
                    response_text=response_text,
                    model=response.model,
                    parse_success=False,
                    error_message=str(exc),
                )
                raise PlanGenerationError(
                    f"Failed to parse AI response for weeks {week_start}-{week_end}: {exc}",
                    raw_chunks=list(raw_chunks),
                ) from exc

            weeks = partial_plan.get("weeks")
            if not isinstance(weeks, list) or len(weeks) == 0:
                error_detail = "AI chunk returned no weeks"
                logger.warning(f"[WORKOUT_PLAN][CHUNK {index}] {error_detail}")
                self._log_ai_response(
                    request_type=f"workout_plan_chunk_{index}",
                    user_id=user_id,
                    prompt=prompt,
                    request_payload=chunk_payload,
                    response_text=response_text,
                    model=response.model,
                    parse_success=False,
                    error_message=error_detail,
                )
                raise PlanGenerationError(
                    f"Failed to generate workouts for weeks {week_start}-{week_end}: no weeks returned",
                    raw_chunks=list(raw_chunks),
                )

            combined_weeks.extend(weeks)
            plan_metadata = self._merge_plan_metadata(plan_metadata, partial_plan)
            previous_summary = self._summarize_weeks_for_context(combined_weeks)

            self._log_ai_response(
                request_type=f"workout_plan_chunk_{index}",
                user_id=user_id,
                prompt=prompt,
                request_payload=chunk_payload,
                response_text=response_text,
                model=response.model,
                parse_success=True,
                error_message=None,
            )

        return plan_metadata, combined_weeks, raw_chunks

    def _assemble_plan_data(
        self,
        *,
        request: WorkoutPlanGenerationRequest,
        total_weeks: int,
        plan_metadata: Dict[str, Any],
        weeks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build the final plan payload combining metadata and weeks."""
        default_title = f"{request.sport_type.title()} Training Plan - {request.level.title()}"
        default_description = plan_metadata.get("summary") or ""

        plan_data: Dict[str, Any] = {
            "title": plan_metadata.get("title") or default_title,
            "description": plan_metadata.get("description") or default_description,
            "sport_type": plan_metadata.get("sport_type") or request.sport_type,
            "level": plan_metadata.get("level") or request.level,
            "goal": plan_metadata.get("goal") or request.goal,
            "duration_weeks": total_weeks,
            "weekly_hours": plan_metadata.get("weekly_hours", request.weekly_hours),
            "weeks": weeks,
        }

        if request.start_date:
            plan_data["start_date"] = request.start_date
        if request.target_date:
            plan_data["end_date"] = request.target_date

        for optional_key in ("phases", "plan_summary", "notes", "macrocycles"):
            if plan_metadata.get(optional_key) is not None:
                plan_data[optional_key] = plan_metadata.get(optional_key)

        return plan_data

    def _build_fallback_plan(
        self,
        request: WorkoutPlanGenerationRequest,
        total_weeks: int,
        raw_chunks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Fallback to a text-based plan when JSON parsing fails."""
        combined_text = "\n\n".join(
            chunk["response"] for chunk in raw_chunks if chunk.get("response")
        )
        if not combined_text:
            combined_text = "AI response could not be parsed."

        fallback_data = {
            "title": f"{request.sport_type.title()} Training Plan - {request.level.title()}",
            "description": combined_text,
            "sport_type": request.sport_type,
            "level": request.level,
            "goal": request.goal,
            "duration_weeks": total_weeks,
            "weekly_hours": request.weekly_hours if request.weekly_hours else None,
            "weeks": [],
        }

        if request.start_date:
            fallback_data["start_date"] = request.start_date
        if request.target_date:
            fallback_data["end_date"] = request.target_date

        return fallback_data

    def _combine_prompts(self, raw_chunks: List[Dict[str, Any]]) -> Optional[str]:
        if not raw_chunks:
            return None
        parts = []
        for chunk in raw_chunks:
            prompt = chunk.get("prompt")
            if not prompt:
                continue
            parts.append(
                f"CHUNK {chunk.get('index')} PROMPT (weeks {chunk.get('week_start')}-{chunk.get('week_end')}):\n{prompt}"
            )
        return "\n\n".join(parts) if parts else None

    def _combine_raw_chunks(self, raw_chunks: List[Dict[str, Any]]) -> Optional[str]:
        if not raw_chunks:
            return None
        parts = []
        for chunk in raw_chunks:
            response = chunk.get("response")
            if response is None:
                continue
            parts.append(
                f"CHUNK {chunk.get('index')} RESPONSE (weeks {chunk.get('week_start')}-{chunk.get('week_end')}):\n{response}"
            )
        return "\n\n".join(parts) if parts else None

    def _resolve_plan_duration(self, request: WorkoutPlanGenerationRequest) -> int:
        """Resolve the number of weeks using duration or start/end dates."""
        if request.duration_weeks:
            return request.duration_weeks

        if request.start_date and request.target_date:
            start = datetime.strptime(request.start_date, "%Y-%m-%d").date()
            end = datetime.strptime(request.target_date, "%Y-%m-%d").date()
            delta_days = (end - start).days
            if delta_days < 0:
                raise ValueError("target_date must be after start_date")
            total_weeks = max(1, math.ceil((delta_days + 1) / 7))
            return total_weeks

        raise ValueError("Provide either duration_weeks or both start_date and target_date")

    def _build_week_ranges(self, total_weeks: int, chunk_size: int) -> List[Tuple[int, int]]:
        return [
            (start, min(start + chunk_size - 1, total_weeks))
            for start in range(1, total_weeks + 1, chunk_size)
        ]

    def _summarize_weeks_for_context(self, weeks: List[Dict[str, Any]]) -> Optional[str]:
        if not weeks:
            return None
        summary_weeks = weeks[-2:] if len(weeks) >= 2 else weeks
        lines = []
        for week in summary_weeks:
            focus = week.get("focus", "N/A")
            workout_count = len(week.get("workouts", [])) if isinstance(week.get("workouts"), list) else 0
            lines.append(f"Week {week.get('week')}: focus={focus}, workouts={workout_count}")
        return "\n".join(lines)

    def _extract_plan_metadata(self, partial_plan: Dict[str, Any]) -> Dict[str, Any]:
        keys = [
            "title",
            "description",
            "sport_type",
            "level",
            "goal",
            "duration_weeks",
            "weekly_hours",
            "phases",
            "plan_summary",
            "notes",
            "macrocycles",
            "start_date",
            "end_date",
        ]
        return {key: partial_plan.get(key) for key in keys if partial_plan.get(key) is not None}

    def _merge_plan_metadata(self, base: Dict[str, Any], partial_plan: Dict[str, Any]) -> Dict[str, Any]:
        if not base:
            return self._extract_plan_metadata(partial_plan)

        merged = dict(base)
        partial_metadata = self._extract_plan_metadata(partial_plan)
        for key, value in partial_metadata.items():
            if key not in merged or merged[key] is None:
                merged[key] = value
        return merged

    def _build_user_state(self, user_id: Optional[int]) -> Optional[Dict[str, Any]]:
        if not self.db or not user_id:
            return None

        readiness_record = (
            self.db.query(DailyReadinessMetrics)
            .filter(DailyReadinessMetrics.user_id == user_id)
            .order_by(DailyReadinessMetrics.metric_date.desc())
            .first()
        )

        weekly_summary = (
            self.db.query(WeeklyTrainingSummary)
            .filter(WeeklyTrainingSummary.user_id == user_id)
            .order_by(WeeklyTrainingSummary.week_start.desc())
            .first()
        )

        if not readiness_record and not weekly_summary:
            return None

        return {
            "readiness_state": readiness_record.readiness_state if readiness_record else None,
            "recovery_index": readiness_record.recovery_index if readiness_record else None,
            "hydration_score": readiness_record.hydration_score if readiness_record else None,
            "injury_risk_score": weekly_summary.injury_risk_score if weekly_summary else None,
        }

    def analyze_workout(self, request: WorkoutAnalysisRequest) -> WorkoutAnalysisResponse:
        """Analyze workout performance using AI"""
        logger.info(f"[WORKOUT_ANALYSIS] Starting workout analysis - analysis_type: {request.analysis_type}")
        logger.debug(f"[WORKOUT_ANALYSIS] Request details: analysis_type={request.analysis_type}, has_workout_data={request.workout_data is not None}, has_performance_metrics={request.performance_metrics is not None}")
        
        prompt = self._build_workout_analysis_prompt(request)
        logger.debug(f"[WORKOUT_ANALYSIS] Prompt built - length: {len(prompt)} characters")
        
        ai_request = AIRequest(
            prompt=prompt,
            context=request.workout_data,
            max_tokens=1000,
            temperature=0.5
        )
        
        response = self.generate_response(ai_request)
        
        self._log_ai_response(
            request_type="workout_analysis",
            user_id=None,
            prompt=prompt,
            request_payload={
                "analysis_type": request.analysis_type,
                "has_workout_data": request.workout_data is not None,
                "has_performance_metrics": request.performance_metrics is not None,
            },
            response_text=response.response,
            model=response.model,
            parse_success=True,
            error_message=None,
        )

        # Parse AI response to extract structured data
        analysis_data = self._parse_workout_analysis(response.response)
        logger.info(f"[WORKOUT_ANALYSIS] Analysis parsed successfully - has_score={analysis_data.get('score') is not None}, recommendations_count={len(analysis_data.get('recommendations', []))}")
        
        result = WorkoutAnalysisResponse(
            analysis=analysis_data.get("analysis", response.response),
            recommendations=analysis_data.get("recommendations", []),
            score=analysis_data.get("score"),
            areas_for_improvement=analysis_data.get("areas_for_improvement", []),
            next_steps=analysis_data.get("next_steps", [])
        )
        
        logger.info(f"[WORKOUT_ANALYSIS] Workout analysis completed successfully")
        return result

    def _log_ai_response(
        self,
        *,
        request_type: str,
        user_id: Optional[int],
        prompt: Optional[str],
        request_payload: Optional[Dict[str, Any]],
        response_text: Optional[str],
        model: Optional[str],
        parse_success: bool,
        error_message: Optional[str],
    ) -> None:
        if not self.db:
            return

        try:
            log_entry = AIResponseLog(
                user_id=user_id,
                request_type=request_type,
                model=model,
                prompt=prompt,
                request_payload=request_payload,
                response=response_text,
                parse_success=parse_success,
                error_message=error_message,
            )
            self.db.add(log_entry)
            self.db.commit()
            logger.debug(
                f"[AI] Logged response for request_type={request_type}, user_id={user_id}, parse_success={parse_success}"
            )
        except Exception as exc:
            self.db.rollback()
            logger.warning(
                f"[AI] Failed to log AI response for request_type={request_type}: {exc}"
            )
    
    def _build_workout_plan_prompt(
        self,
        request: WorkoutPlanGenerationRequest,
        *,
        duration_weeks: int,
        week_start: Optional[int] = None,
        week_end: Optional[int] = None,
        previous_weeks_summary: Optional[str] = None,
    ) -> str:
        """Build prompt for workout plan generation"""
        weekly_hours_note = f"Weekly training hours: {request.weekly_hours}" if request.weekly_hours else "Weekly training hours: Not specified - YOU decide the optimal training volume based on the athlete's level and goals"
        
        prompt = f"""
        Create a detailed {request.sport_type} training plan for a {request.level} athlete.
        
        Goal: {request.goal}
        Duration: {duration_weeks} weeks
        {weekly_hours_note}
        
        Please provide a structured training plan that includes:
        1. Weekly breakdown with specific workouts
        2. Workout types and intensities (use heart rate zones, power zones, or pace zones as appropriate)
        3. Detailed session structures (warm-up, main set, cooldown) with explicit steps, durations, repeats, and targets
        4. Progression over the {duration_weeks} weeks
        5. Recovery and rest days
        6. Key training phases
        
        """
        if week_start is not None and week_end is not None:
            prompt += f"""
        === GENERATION SCOPE ===
        - Generate ONLY weeks {week_start} through {week_end} (inclusive) of the full {duration_weeks}-week plan.
        - Weeks must be numbered using the absolute plan numbering (do not restart from 1 in each chunk).
        - Ensure continuity with the preceding weeks.
        """
            if previous_weeks_summary:
                prompt += f"""
        === PREVIOUS WEEKS SUMMARY (for continuity) ===
        {previous_weeks_summary}
        """
        
        # Gestione user_profile - può contenere: age, weight, height, experience_years, 
        # threshold_hr, ftp, max_hr, resting_hr, hr_zones, power_zones, pace_zones, 
        # physical_notes (contains any physical notes, injuries, limitations, health conditions, etc.)
        # E metriche di performance: hr_max, hr_rest, threshold_hr, ftp, threshold_pace, vo2max, etc.
        if request.user_profile:
            prompt += "\n\n=== USER PROFILE ==="
            prompt += f"\n{json.dumps(request.user_profile, indent=2)}"
            prompt += "\n\nUse this information to personalize the training plan:"
            prompt += "\n- Adjust intensities based on provided thresholds (HR zones, power zones, pace zones)"
            prompt += "\n- Consider age and experience level for recovery and progression"
            prompt += "\n- Use weight and physical characteristics to adjust volume and intensity recommendations"
            prompt += "\n- Incorporate any existing fitness metrics (threshold values, max values, etc.) into workout prescriptions"
            
            # Gestione PERFORMANCE METRICS se presenti nel user_profile
            has_performance_metrics = any(key in request.user_profile for key in [
                'hr_max', 'hr_rest', 'threshold_hr', 'hrr', 'custom_threshold_hr',
                'threshold_pace', 'critical_speed', 'vla',
                'ftp', 'wkg',
                'vo2max',
                'hr_zones', 'pace_zones', 'power_zones',
                'hr_zones_source', 'pace_zones_source', 'power_zones_source'
            ])
            
            if has_performance_metrics:
                prompt += "\n\n=== PERFORMANCE METRICS ==="
                prompt += "\nUSE EXACT ZONE VALUES PROVIDED - do not estimate or approximate."
                
                # HR Metrics (compact)
                if request.user_profile.get('hr_zones') or request.user_profile.get('threshold_hr') or request.user_profile.get('hr_max'):
                    hr_info = []
                    if request.user_profile.get('hr_max'):
                        hr_info.append(f"HR Max: {request.user_profile.get('hr_max')} bpm")
                    if request.user_profile.get('hr_rest'):
                        hr_info.append(f"HR Rest: {request.user_profile.get('hr_rest')} bpm")
                    if request.user_profile.get('threshold_hr'):
                        hr_info.append(f"Threshold: {request.user_profile.get('threshold_hr')} bpm")
                    if request.user_profile.get('hr_zones'):
                        zones = request.user_profile.get('hr_zones')
                        if isinstance(zones, dict):
                            hr_info.append(f"Zones: {', '.join([f'{k.upper()}={v}' for k, v in zones.items()])}")
                    prompt += f"\nHR: {', '.join(hr_info)}"
                
                # Pace Metrics (compact)
                if request.user_profile.get('pace_zones') or request.user_profile.get('threshold_pace'):
                    pace_info = []
                    if request.user_profile.get('threshold_pace'):
                        pace_info.append(f"Threshold: {request.user_profile.get('threshold_pace')} min/km")
                    if request.user_profile.get('critical_speed'):
                        pace_info.append(f"Critical Speed: {request.user_profile.get('critical_speed')} km/h")
                    if request.user_profile.get('pace_zones'):
                        zones = request.user_profile.get('pace_zones')
                        if isinstance(zones, dict):
                            pace_info.append(f"Zones: {', '.join([f'{k.upper()}={v}' for k, v in zones.items()])}")
                    prompt += f"\nPace: {', '.join(pace_info)}"
                
                # Power Metrics (compact)
                if request.user_profile.get('power_zones') or request.user_profile.get('ftp'):
                    power_info = []
                    if request.user_profile.get('ftp'):
                        power_info.append(f"FTP: {request.user_profile.get('ftp')}W")
                    if request.user_profile.get('wkg'):
                        power_info.append(f"W/kg: {request.user_profile.get('wkg')}")
                    if request.user_profile.get('power_zones'):
                        zones = request.user_profile.get('power_zones')
                        if isinstance(zones, dict):
                            power_info.append(f"Zones: {', '.join([f'{k.upper()}={v}W' for k, v in zones.items()])}")
                    prompt += f"\nPower: {', '.join(power_info)}"
                
                # Advanced Metrics
                if request.user_profile.get('vo2max'):
                    prompt += f"\nVO2max: {request.user_profile.get('vo2max')} ml/kg/min"
                
                # Preferred zone type
                preferred_zone_type = request.user_profile.get('preferred_zone_type', 'hr')
                prompt += f"\nPreferred zone type: {preferred_zone_type.upper()} (prioritize this in prescriptions)"
                
                prompt += "\n\nCRITICAL: Use exact zone values from above. For Z4 use threshold values, for Z5 use 105-120% of threshold."
            
            # Gestione specifica per note fisiche e problemi - tutto dentro physical_notes
            if request.user_profile.get("physical_notes"):
                prompt += "\n\n⚠️ IMPORTANT - PHYSICAL NOTES/LIMITATIONS:"
                prompt += f"\n{request.user_profile.get('physical_notes')}"
                prompt += "\n- CRITICAL: Adapt workouts to accommodate any physical limitations, injuries, or health conditions mentioned above"
                prompt += "\n- Modify or replace exercises that may aggravate existing conditions or injuries"
                prompt += "\n- Include appropriate modifications, alternatives, or recovery considerations"
                prompt += "\n- Prioritize safety and injury prevention over intensity"
                prompt += "\n- If unclear about modifications, suggest consulting with a healthcare provider"
                prompt += "\n- Adjust training volume, intensity, and exercise selection based on any physical constraints described"
        else:
            prompt += "\n\n=== USER PROFILE ==="
            prompt += "\nNo specific user profile provided - create a generic plan suitable for the specified level."
            prompt += "\nUse standard zone definitions and progressions appropriate for the level."
        
        # Gestione preferences
        if request.preferences:
            prompt += "\n\n=== USER PREFERENCES (INDICATIVE ONLY) ==="
            prompt += f"\n{json.dumps(request.preferences, indent=2)}"
            prompt += "\n\nIMPORTANT: These preferences are INDICATIVE ONLY, not strict constraints:"
            prompt += "\n- Use preferred training days and schedule constraints as a GUIDELINE, but you have full autonomy to optimize the plan"
            prompt += "\n- Consider intensity preferences, but prioritize optimal training structure"
            prompt += "\n- Equipment availability is a factor, but adapt the plan for best results"
            prompt += "\n- YOU decide the optimal number of workouts per week and session durations based on training science"
            prompt += "\n- Balance different disciplines optimally - don't limit yourself to user preferences"
            
            # Se ci sono giorni disponibili o durata minima, trattali come indicazioni
            if request.preferences.get("available_days_per_week"):
                prompt += f"\n- User indicated ~{request.preferences.get('available_days_per_week')} days/week available - use as REFERENCE, not constraint"
            if request.preferences.get("min_session_duration_minutes"):
                prompt += f"\n- User indicated minimum session duration of ~{request.preferences.get('min_session_duration_minutes')} minutes - use as REFERENCE, but optimize for best training outcomes"
        
        if request.race_distance_km or request.race_type:
            prompt += "\n\n=== RACE SPECIFICATIONS ==="
            if request.race_distance_km:
                prompt += f"\n- Target race distance: {request.race_distance_km} km (running/trail)"
            if request.race_type:
                prompt += f"\n- Triathlon race type: {request.race_type.replace('_', ' ').title()}"
            prompt += "\n- Structure the training phases to peak for this event, aligning long workouts, simulations, and taper accordingly."
        
        prompt += """
        
        Format the response as a JSON object with the following structure:
        {
            "title": "Plan title",
            "description": "Brief description",
            "weeks": [
                {
                    "week": 1,
                    "focus": "Base building",
                    "workouts": [
                        {
                            "day": "Monday",
                            "type": "Endurance",
                            "sport": "run",
                            "duration_minutes": 60,
                            "intensity": "Z2",
                            "rpe_target": 6,
                            "zone": "Z2",
                            "description": "Easy aerobic run",
                            "structure": {
                                "sport": "run",
                                "segments": [
                                    {
                                        "segment_type": "warmup",
                                        "name": "Warm-up",
                                        "steps": [
                                            {
                                                "step_type": "steady",
                                                "duration": {"type": "time", "seconds": 600},
                                                "target": {"type": "zone", "zone": "Z2"},
                                                "notes": "Easy jog"
                                            }
                                        ]
                                    },
                                    {
                                        "segment_type": "main",
                                        "name": "Intervals",
                                        "steps": [
                                            {
                                                "step_type": "repeat",
                                                "repeat": 6,
                                                "steps": [
                                                    {
                                                        "step_type": "interval",
                                                        "duration": {"type": "time", "seconds": 120},
                                                        "target": {"type": "zone", "zone": "Z4"},
                                                        "notes": "Uphill sprint"
                                                    },
                                                    {
                                                        "step_type": "recovery",
                                                        "duration": {"type": "time", "seconds": 120},
                                                        "target": {"type": "zone", "zone": "Z2"},
                                                        "notes": "Jog back down"
                                                    }
                                                ]
                                            }
                                        ]
                                    },
                                    {
                                        "segment_type": "cooldown",
                                        "steps": [
                                            {
                                                "step_type": "steady",
                                                "duration": {"type": "time", "seconds": 600},
                                                "target": {"type": "zone", "zone": "Z1"},
                                                "notes": "Easy jog"
                                            }
                                        ]
                                    }
                                ],
                                "metadata": {
                                    "focus": "Base building with speed introduction",
                                    "rpe_target": 6,
                                    "description": "Maintain relaxed form during repeats"
                                }
                            },
                            "modifications": "Optional: modifications if physical limitations exist"
                        }
                    ]
                }
            ]
        }
        
        Important:
        - For running/trail workouts use heart-rate or pace zones Z1-Z5; for cycling use Z1-Z7; ensure targets match provided user thresholds when available
        - If HR zones are provided in user_profile, include exact HR ranges in the structure targets (type: "heart_rate")
        - If power zones are provided, use power targets (e.g., "200-250W")
        - If pace zones are provided, use pace targets (e.g., "5:00-5:30 min/km")
        - Every workout MUST contain a structure object with segments and steps; do not fallback to plain text descriptions
        - Every workout MUST include warmup and cooldown segments, each with at least one step describing duration and target
        - Adjust workout prescriptions based on user's physical characteristics and experience
        - Ensure progression is appropriate for the user's level and available training time
        - ALWAYS prioritize safety: if physical_notes are present, carefully read and adapt workouts accordingly
        - Include modifications or alternatives in the description or modifications field when necessary to accommodate physical constraints
        - The output MUST be valid JSON (double quotes for all keys/strings, no comments, no trailing commas, no explanations outside the JSON payload)
        """

        if week_start is not None and week_end is not None:
            prompt += f"""
        - ONLY include weeks {week_start}-{week_end} in the weeks array.
        - Summaries, phases, and other metadata should remain consistent with a {duration_weeks}-week plan.
        """
        
        return prompt
    
    def _build_workout_analysis_prompt(self, request: WorkoutAnalysisRequest) -> str:
        """Build prompt for workout analysis"""
        prompt = f"""
        Analyze this {request.analysis_type} workout data and provide insights:
        
        Workout Data:
        {json.dumps(request.workout_data, indent=2)}
        """
        
        if request.performance_metrics:
            prompt += f"\n\nPerformance Metrics:\n{json.dumps(request.performance_metrics, indent=2)}"
        
        prompt += f"""
        
        Please provide:
        1. Analysis of the workout performance
        2. Specific recommendations for improvement
        3. A performance score (1-10)
        4. Areas that need improvement
        5. Next steps for training
        
        Format as JSON:
        {{
            "analysis": "Detailed analysis text",
            "recommendations": ["rec1", "rec2"],
            "score": 8.5,
            "areas_for_improvement": ["area1", "area2"],
            "next_steps": ["step1", "step2"]
        }}
        """
        
        return prompt
    
    def _parse_workout_analysis(self, response: str) -> Dict[str, Any]:
        """Parse AI response for workout analysis"""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Fallback parsing for non-JSON responses
            return {
                "analysis": response,
                "recommendations": [],
                "score": None,
                "areas_for_improvement": [],
                "next_steps": []
            }
    
    def _generate_mock_workout_plan(self, request: WorkoutPlanGenerationRequest, prompt: str, ai_request: AIRequest) -> Dict[str, Any]:
        """Generate mock workout plan for testing - uses same data as real LLM"""
        logger.info(f"[WORKOUT_PLAN][MOCK] Generating mock workout plan")
        logger.debug(f"[WORKOUT_PLAN][MOCK] Received prompt length: {len(prompt)}")
        logger.debug(f"[WORKOUT_PLAN][MOCK] AIRequest details: prompt_length={len(ai_request.prompt)}, context_type={type(ai_request.context).__name__ if ai_request.context else None}")
        
        # Log all data that would be sent to LLM
        mock_request_summary = {
            "sport_type": request.sport_type,
            "level": request.level,
            "goal": request.goal,
            "duration_weeks": request.duration_weeks,
            "weekly_hours": request.weekly_hours,
            "user_profile_keys": list(request.user_profile.keys()) if request.user_profile else None,
            "user_profile": request.user_profile,
            "preferences": request.preferences,
                "race_distance_km": request.race_distance_km,
                "race_type": request.race_type,
            "prompt_length": len(prompt),
            "ai_request_context": ai_request.context
        }
        logger.info(f"[WORKOUT_PLAN][MOCK] Full request data that would be sent to LLM: {json.dumps(mock_request_summary, indent=2, default=str)}")
        
        if request.sport_type.lower() == "running":
            result = self._generate_mock_running_plan(request, prompt, ai_request)
        elif request.sport_type.lower() == "triathlon":
            result = self._generate_mock_triathlon_plan(request, prompt, ai_request)
        else:
            result = self._generate_mock_generic_plan(request, prompt, ai_request)
        
        logger.debug(f"[WORKOUT_PLAN][MOCK] Mock plan generated - result keys: {list(result.keys())}")
        return result
    
    def _generate_mock_running_plan(self, request: WorkoutPlanGenerationRequest, prompt: str, ai_request: AIRequest) -> Dict[str, Any]:
        """Return the canned 7-week running plan for mock mode, adjusting metadata to the request."""
        logger.info(f"[WORKOUT_PLAN][MOCK][RUNNING] Generating mock running plan")
        logger.debug(f"[WORKOUT_PLAN][MOCK][RUNNING] Prompt received: {len(prompt)} chars")
        logger.debug(f"[WORKOUT_PLAN][MOCK][RUNNING] User profile: {json.dumps(request.user_profile, indent=2, default=str) if request.user_profile else None}")
        logger.debug(f"[WORKOUT_PLAN][MOCK][RUNNING] Preferences: {json.dumps(request.preferences, indent=2, default=str) if request.preferences else None}")

        default_hours = {
            "beginner": 4.0,
            "intermediate": 6.0,
            "advanced": 8.0,
        }
        weekly_hours = request.weekly_hours or default_hours.get(request.level.lower(), 6.0)

        plan = deepcopy(MOCK_RUNNING_PLAN_STANDARD)
        plan["level"] = request.level
        plan["goal"] = request.goal
        plan["weekly_hours"] = weekly_hours
        plan["duration_weeks"] = len(plan.get("weeks", []))

        title_suffix: List[str] = []
        description_suffix: List[str] = []

        if request.race_distance_km:
            title_suffix.append(f"{request.race_distance_km:g} km")
            description_suffix.append(f"Target race distance: {request.race_distance_km:g} km.")
        if request.race_type:
            readable_type = request.race_type.replace("_", " ").title()
            title_suffix.append(readable_type)
            description_suffix.append(f"Race type: {readable_type}.")

        if title_suffix:
            plan["title"] = f"{plan['title']} ({', '.join(title_suffix)})"
        plan["description"] = " ".join([plan["description"], *description_suffix]).strip()

        return plan
    
    def _generate_mock_triathlon_plan(self, request: WorkoutPlanGenerationRequest, prompt: str, ai_request: AIRequest) -> Dict[str, Any]:
        """Generate mock triathlon plan (2 months to Dec 24, 2025) - uses same data as real LLM"""
        logger.info(f"[WORKOUT_PLAN][MOCK][TRIATHLON] Generating mock triathlon plan")
        logger.debug(f"[WORKOUT_PLAN][MOCK][TRIATHLON] Prompt received: {len(prompt)} chars")
        logger.debug(f"[WORKOUT_PLAN][MOCK][TRIATHLON] User profile: {json.dumps(request.user_profile, indent=2, default=str) if request.user_profile else None}")
        logger.debug(f"[WORKOUT_PLAN][MOCK][TRIATHLON] Preferences: {json.dumps(request.preferences, indent=2, default=str) if request.preferences else None}")
        
        # Use default weekly hours if not specified (based on level)
        default_hours = {
            "beginner": 6.0,
            "intermediate": 10.0,
            "advanced": 14.0
        }
        weekly_hours = request.weekly_hours or default_hours.get(request.level.lower(), 10.0)
        logger.debug(f"[WORKOUT_PLAN][MOCK][TRIATHLON] Using weekly_hours: {weekly_hours} (from request: {request.weekly_hours})")
        
        weeks = []
        start_date = datetime(2025, 10, 25)
        race_type = request.race_type or "olympic"
        
        for week_num in range(1, 9):  # 8 weeks = 2 months
            week_start = start_date + timedelta(weeks=week_num-1)
            week_end = week_start + timedelta(days=6)
            
            week_data = {
                "week": week_num,
                "focus": self._get_triathlon_focus(week_num),
                "total_hours": weekly_hours,
                "workouts": self._generate_triathlon_workouts(week_num, weekly_hours),
                "week_start": week_start.strftime("%Y-%m-%d"),
                "week_end": week_end.strftime("%Y-%m-%d")
            }
            weeks.append(week_data)
        
        description_suffix = f" ({race_type.replace('_', ' ').title()})" if race_type else ""
        
        return {
            "title": f"Triathlon Training Plan - {request.goal}{description_suffix}",
            "description": f"8-week triathlon plan to achieve {request.goal} by December 24, 2025{description_suffix}.",
            "sport_type": "triathlon",
            "level": request.level,
            "goal": request.goal,
            "duration_weeks": 8,
            "weekly_hours": weekly_hours,
            "start_date": "2025-10-25",
            "end_date": "2025-12-24",
            "weeks": weeks
        }
    
    def _generate_mock_generic_plan(self, request: WorkoutPlanGenerationRequest, prompt: str, ai_request: AIRequest) -> Dict[str, Any]:
        """Generate generic mock plan - uses same data as real LLM"""
        logger.info(f"[WORKOUT_PLAN][MOCK][GENERIC] Generating mock generic plan")
        logger.debug(f"[WORKOUT_PLAN][MOCK][GENERIC] Prompt received: {len(prompt)} chars")
        logger.debug(f"[WORKOUT_PLAN][MOCK][GENERIC] User profile: {json.dumps(request.user_profile, indent=2, default=str) if request.user_profile else None}")
        logger.debug(f"[WORKOUT_PLAN][MOCK][GENERIC] Preferences: {json.dumps(request.preferences, indent=2, default=str) if request.preferences else None}")
        
        # Use default weekly hours if not specified
        default_hours = {
            "beginner": 4.0,
            "intermediate": 6.0,
            "advanced": 8.0
        }
        weekly_hours = request.weekly_hours or default_hours.get(request.level.lower(), 6.0)
        logger.debug(f"[WORKOUT_PLAN][MOCK][GENERIC] Using weekly_hours: {weekly_hours} (from request: {request.weekly_hours})")
        
        return {
            "title": f"{request.sport_type.title()} Training Plan - {request.goal}",
            "description": f"Mock training plan for {request.sport_type}",
            "sport_type": request.sport_type,
            "level": request.level,
            "goal": request.goal,
            "duration_weeks": request.duration_weeks,
            "weekly_hours": weekly_hours
        }
    
    def _get_running_focus(self, week_num: int) -> str:
        """Get running focus for specific week"""
        focuses = [
            "Base Building", "Base Building", "Endurance", "Endurance",
            "Speed Work", "Speed Work", "Taper", "Race Week"
        ]
        return focuses[min(week_num-1, len(focuses)-1)]
    
    def _get_triathlon_focus(self, week_num: int) -> str:
        """Get triathlon focus for specific week"""
        focuses = [
            "Base Building", "Base Building", "Brick Training", "Brick Training",
            "Speed Work", "Speed Work", "Taper", "Race Week"
        ]
        return focuses[min(week_num-1, len(focuses)-1)]
    
    def _generate_running_workouts(self, week_num: int, weekly_hours: float) -> list:
        """Generate running workouts for a week"""
        workouts = []
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        # Base workouts
        base_workouts = [
            {"type": "Easy Run", "duration_minutes": 45, "intensity": "Z2", "description": "Easy aerobic run"},
            {"type": "Tempo Run", "duration_minutes": 30, "intensity": "Z3", "description": "Comfortably hard pace"},
            {"type": "Long Run", "duration_minutes": 90, "intensity": "Z2", "description": "Long endurance run"},
            {"type": "Recovery Run", "duration_minutes": 30, "intensity": "Z1", "description": "Easy recovery run"},
            {"type": "Interval Training", "duration_minutes": 60, "intensity": "Z4", "description": "High intensity intervals"}
        ]
        
        # Select workouts based on week and hours
        if week_num <= 2:
            selected = [0, 1, 2, 3]  # Base building
        elif week_num <= 4:
            selected = [0, 1, 2, 4]  # Endurance + speed
        elif week_num <= 6:
            selected = [0, 1, 2, 4]  # Speed work
        else:
            selected = [0, 2, 3]  # Taper
        
        for i, workout_idx in enumerate(selected[:4]):  # Max 4 workouts per week
            workout = base_workouts[workout_idx].copy()
            workout["day"] = days[i]
            workout["rpe_target"] = 6 + (workout_idx % 3)
            workout["sport"] = "run"
            zone = workout.get("intensity", "Z2").upper()
            workout["zone"] = zone if zone.startswith("Z") else "Z2"
            workout["structure"] = self._build_mock_structure(
                sport="run",
                duration_minutes=workout["duration_minutes"],
                zone=workout["zone"],
                description=workout.get("description", ""),
                workout_type=workout.get("type", "Run"),
            )
            workouts.append(workout)
        
        return workouts
    
    def _generate_triathlon_workouts(self, week_num: int, weekly_hours: float) -> list:
        """Generate triathlon workouts for a week"""
        workouts = []
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        # Triathlon workouts
        tri_workouts = [
            {"type": "Swim", "duration_minutes": 45, "intensity": "Z2", "description": "Easy swim technique work"},
            {"type": "Bike", "duration_minutes": 60, "intensity": "Z2", "description": "Endurance bike ride"},
            {"type": "Run", "duration_minutes": 30, "intensity": "Z2", "description": "Easy transition run"},
            {"type": "Brick", "duration_minutes": 90, "intensity": "Z3", "description": "Bike + Run brick workout"},
            {"type": "Swim Intervals", "duration_minutes": 60, "intensity": "Z4", "description": "Swim interval training"},
            {"type": "Bike Tempo", "duration_minutes": 45, "intensity": "Z3", "description": "Tempo bike workout"},
            {"type": "Recovery", "duration_minutes": 30, "intensity": "Z1", "description": "Easy recovery workout"}
        ]
        
        # Select workouts based on week
        if week_num <= 2:
            selected = [0, 1, 2, 6]  # Base building
        elif week_num <= 4:
            selected = [0, 1, 3, 2]  # Brick training
        elif week_num <= 6:
            selected = [4, 5, 3, 2]  # Speed work
        else:
            selected = [0, 1, 2, 6]  # Taper
        
        for i, workout_idx in enumerate(selected[:4]):  # Max 4 workouts per week
            workout = tri_workouts[workout_idx].copy()
            workout["day"] = days[i]
            workout["rpe_target"] = 6 + (workout_idx % 3)
            sport = self._infer_mock_sport_from_type(workout.get("type"))
            workout["sport"] = sport
            zone = workout.get("intensity", "Z2").upper()
            if sport == "bike" and zone == "Z3":
                workout["zone"] = "Z3"
            else:
                workout["zone"] = zone if zone.startswith("Z") else "Z2"
            workout["structure"] = self._build_mock_structure(
                sport=sport,
                duration_minutes=workout["duration_minutes"],
                zone=workout["zone"],
                description=workout.get("description", ""),
                workout_type=workout.get("type", "Session"),
            )
            workouts.append(workout)
        
        return workouts

    def _build_mock_structure(
        self,
        *,
        sport: str,
        duration_minutes: int,
        zone: str,
        description: str,
        workout_type: str,
    ) -> Dict[str, Any]:
        total_seconds = max(int(duration_minutes * 60), 600)
        warmup_seconds = min(600, max(total_seconds // 6, 300))
        cooldown_seconds = warmup_seconds
        main_seconds = max(total_seconds - warmup_seconds - cooldown_seconds, 300)

        warmup_step = {
            "step_type": "steady",
            "duration": {"type": "time", "seconds": warmup_seconds},
            "target": {"type": "zone", "zone": "Z2" if sport != "bike" else "Z2"},
            "notes": "Gradually build effort" if sport != "swim" else "Smooth easy strokes",
        }

        cooldown_step = {
            "step_type": "steady",
            "duration": {"type": "time", "seconds": cooldown_seconds},
            "target": {"type": "zone", "zone": "Z1"},
            "notes": "Relax and lower intensity",
        }

        if "interval" in workout_type.lower():
            interval_seconds = max(main_seconds // 6, 90)
            recovery_seconds = interval_seconds
            repeat_count = max(main_seconds // (interval_seconds + recovery_seconds), 3)
            repeat_step = {
                "step_type": "repeat",
                "repeat": int(repeat_count),
                "steps": [
                    {
                        "step_type": "interval",
                        "duration": {"type": "time", "seconds": interval_seconds},
                        "target": {"type": "zone", "zone": zone},
                        "notes": description or "Hard effort",
                    },
                    {
                        "step_type": "recovery",
                        "duration": {"type": "time", "seconds": recovery_seconds},
                        "target": {"type": "zone", "zone": "Z2"},
                        "notes": "Controlled recovery",
                    },
                ],
            }
            main_steps = [repeat_step]
        else:
            main_steps = [
                {
                    "step_type": "steady",
                    "duration": {"type": "time", "seconds": main_seconds},
                    "target": {"type": "zone", "zone": zone},
                    "notes": description or "Sustain target intensity",
                }
            ]

        return {
            "sport": sport,
            "segments": [
                {"segment_type": "warmup", "name": "Warm-up", "steps": [warmup_step]},
                {"segment_type": "main", "name": "Main Set", "steps": main_steps},
                {"segment_type": "cooldown", "name": "Cool-down", "steps": [cooldown_step]},
            ],
            "metadata": {
                "description": description,
            },
        }

    @staticmethod
    def _infer_mock_sport_from_type(workout_type: Optional[str]) -> str:
        if not workout_type:
            return "run"
        lowered = workout_type.lower()
        if "swim" in lowered:
            return "swim"
        if "bike" in lowered or "ride" in lowered or "brick" in lowered:
            return "bike"
        if "run" in lowered:
            return "run"
        return "triathlon"


WORKOUT_PLAN_JSON_SCHEMA: Dict[str, Any] = {
    "name": "workout_plan_chunk",
    "schema": {
        "type": "object",
        "required": ["weeks"],
        "properties": {
            "title": {"type": ["string", "null"]},
            "description": {"type": ["string", "null"]},
            "summary": {"type": ["string", "null"]},
            "notes": {"type": ["string", "null"]},
            "weeks": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["week", "focus", "workouts"],
                    "properties": {
                        "week": {"type": "integer", "minimum": 1},
                        "focus": {"type": "string"},
                        "week_start": {"type": ["string", "null"]},
                        "week_end": {"type": ["string", "null"]},
                        "total_hours": {"type": ["number", "null"], "minimum": 0},
                        "workouts": {
                            "type": "array",
                            "minItems": 1,
                            "items": {
                                "type": "object",
                                "required": ["day", "sport", "duration_minutes", "structure"],
                                "properties": {
                                    "day": {"type": "string"},
                                    "type": {"type": ["string", "null"]},
                                    "sport": {"type": "string"},
                                    "duration_minutes": {"type": ["number", "integer"], "minimum": 0.1},
                                    "intensity": {"type": ["string", "null"]},
                                    "rpe_target": {"type": ["integer", "null"], "minimum": 1},
                                    "zone": {"type": ["string", "null"]},
                                    "description": {"type": ["string", "null"]},
                                    "modifications": {"type": ["string", "null"]},
                                    "notes": {"type": ["string", "null"]},
                                    "structure": {
                                        "type": "object",
                                        "required": ["sport", "segments"],
                                        "properties": {
                                            "sport": {"type": "string"},
                                            "segments": {
                                                "type": "array",
                                                "minItems": 1,
                                                "items": {"$ref": "#/definitions/segment"}
                                            },
                                            "metadata": {
                                                "anyOf": [
                                                    {"$ref": "#/definitions/structureMetadata"},
                                                    {"type": "null"}
                                                ]
                                            },
                                            "equipment": {
                                                "anyOf": [
                                                    {
                                                        "type": "array",
                                                        "items": {"type": "string"}
                                                    },
                                                    {"type": "null"}
                                                ]
                                            }
                                        },
                                        "additionalProperties": False
                                    }
                                },
                                "additionalProperties": False
                            }
                        }
                    },
                    "additionalProperties": False
                }
            }
        },
        "additionalProperties": False,
        "definitions": {
            "duration": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["time", "distance", "repetitions"]},
                    "seconds": {"type": "integer", "minimum": 1},
                    "distance": {"type": "number", "minimum": 0.1},
                    "repetitions": {"type": "integer", "minimum": 1},
                    "units": {"type": ["string", "null"]}
                },
                "additionalProperties": False
            },
            "target": {
                "type": "object",
                "properties": {
                    "type": {"type": ["string", "null"]},
                    "zone": {"type": ["string", "null"]},
                    "min_value": {"type": ["number", "null"]},
                    "max_value": {"type": ["number", "null"]},
                    "units": {"type": ["string", "null"]}
                },
                "additionalProperties": False
            },
            "segmentStep": {
                "type": "object",
                "required": ["step_type"],
                "properties": {
                    "step_type": {"type": "string"},
                    "name": {"type": ["string", "null"]},
                    "repeat": {"type": ["integer", "null"], "minimum": 1},
                    "duration": {
                        "anyOf": [
                            {"$ref": "#/definitions/duration"},
                            {"type": "null"}
                        ]
                    },
                    "target": {
                        "anyOf": [
                            {"$ref": "#/definitions/target"},
                            {"type": "null"}
                        ]
                    },
                    "notes": {"type": ["string", "null"]},
                    "steps": {
                        "anyOf": [
                            {
                                "type": "array",
                                "items": {"$ref": "#/definitions/segmentStep"}
                            },
                            {"type": "null"}
                        ]
                    }
                },
                "additionalProperties": False
            },
            "segment": {
                "type": "object",
                "required": ["segment_type", "steps"],
                "properties": {
                    "segment_type": {"type": "string"},
                    "name": {"type": ["string", "null"]},
                    "steps": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"$ref": "#/definitions/segmentStep"}
                    }
                },
                "additionalProperties": False
            },
            "structureMetadata": {
                "type": "object",
                "properties": {
                    "focus": {"type": ["string", "null"]},
                    "rpe_target": {"type": ["integer", "null"], "minimum": 1},
                    "description": {"type": ["string", "null"]},
                    "notes": {"type": ["string", "null"]}
                },
                "additionalProperties": False
            }
        }
    }
}
