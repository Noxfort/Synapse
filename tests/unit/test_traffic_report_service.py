# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems
#
# File: tests/unit/test_traffic_report_service.py
# Author: Gabriel Moraes
# Date: 2026-09-04

import pytest
from unittest.mock import MagicMock
from src.services.traffic_report_service import TrafficReportService
from src.handlers.system_handler import SystemCommandHandler
from src.ipc.ipc_protocol import IpcMessage


def test_traffic_report_service_default_build():
    service = TrafficReportService()
    output = service.build_report()

    assert "report" in output
    assert "formatted_markdown" in output

    report = output["report"]
    assert report["protocol"].startswith("RELATORIO-TRAFEGO-2026-")
    assert report["processNumber"].startswith("PA-SMT-2026/")
    assert report["cityHall"] == "PREFEITURA DO MUNICÍPIO DE SÃO PAULO"
    assert report["authorityName"] == "Gabriel Moraes"

    # Verify macro summary
    summary = report["networkSummary"]
    assert summary["corridorsMonitored"] == 4
    assert summary["controlledIntersections"] == 18
    assert summary["totalSensorsCount"] >= 5

    # Verify sensors
    sensors = report["sensors"]
    assert len(sensors) >= 5
    for s in sensors:
        assert "id" in s
        assert "junction" in s
        assert "measuredSpeed" in s
        assert "saturationDegree" in s

    # Verify quesitos
    quesitos = report["quesitos"]
    assert len(quesitos) == 5
    for q in quesitos:
        assert q["answer"] in ("SIM", "NÃO", "PARCIALMENTE")
        assert len(q["technicalJustification"]) > 20

    # Verify legal framing
    assert len(report["legalFraming"]) >= 5

    # Verify markdown
    md = output["formatted_markdown"]
    assert report["protocol"] in md
    assert report["processNumber"] in md
    assert "ABNT NBR 10719" in md
    assert "Código de Trânsito Brasileiro" in md


def test_traffic_report_service_custom_municipal_config():
    service = TrafficReportService()
    custom_cfg = {
        "cityHall": "PREFEITURA DE CURITIBA",
        "department": "URBS - URBANIZAÇÃO DE CURITIBA S.A.",
        "authorityName": "Engenheiro Chefe de Tráfego",
        "authorityRole": "Superintendente de Trânsito",
        "registrationNumber": "CREA-PR 99281",
        "processPrefix": "PA-URBS-2026/",
    }
    output = service.build_report(municipal_config=custom_cfg)
    report = output["report"]

    assert report["cityHall"] == "PREFEITURA DE CURITIBA"
    assert report["department"] == "URBS - URBANIZAÇÃO DE CURITIBA S.A."
    assert report["authorityName"] == "Engenheiro Chefe de Tráfego"
    assert report["processNumber"].startswith("PA-URBS-2026/")


def test_system_handler_generate_official_report_ipc():
    mock_controller = MagicMock()
    mock_controller.app_state = MagicMock()
    mock_controller.app_state.get_all_data_sources.return_value = []

    handler = SystemCommandHandler(controller=mock_controller)
    msg = IpcMessage(
        id="req_123",
        action="generate_official_report",
        payload={"municipal_config": {"authorityName": "Auditor Teste"}},
    )

    resp = handler.handle_generate_official_report(msg)
    assert resp["success"] is True
    assert "report" in resp
    assert resp["report"]["authorityName"] == "Auditor Teste"
    assert "formatted_markdown" in resp


def test_traffic_report_service_interfaces():
    from src.interfaces.reports import ITrafficReportService, IReportFormatter
    from src.formatters.abnt_markdown_formatter import AbntMarkdownReportFormatter

    service = TrafficReportService()
    formatter = AbntMarkdownReportFormatter()

    assert isinstance(service, ITrafficReportService)
    assert isinstance(formatter, IReportFormatter)


def test_traffic_report_service_custom_formatter_injection():
    class DummyHtmlFormatter:
        def format(self, report_data):
            return f"<html><body><h1>Protocol: {report_data['protocol']}</h1></body></html>"

    custom_formatter = DummyHtmlFormatter()
    service = TrafficReportService(formatter=custom_formatter)
    output = service.build_report()

    assert output["formatted_markdown"].startswith("<html><body><h1>Protocol: RELATORIO-TRAFEGO-2026-")
    assert "</h1></body></html>" in output["formatted_markdown"]


def test_traffic_report_service_custom_template(tmp_path):
    import json

    custom_template = {
        "systemVersion": "SYNAPSE Custom v9.9",
        "auditObjective": "Auditoria Experimental Personalizada.",
        "observedTrafficDiagnosis": "Diagnóstico de Teste Unitário.",
        "adaptiveActionExecuted": "Ação Experimental Injetada.",
        "defaultAttribution": {
            "cityHall": "PREFEITURA DE FLORIANÓPOLIS",
            "department": "IPUF - INSTITUTO DE PLANEJAMENTO URBANO",
            "authorityName": "Auditor Sênior",
            "authorityRole": "Engenheiro de Tráfego",
            "registrationNumber": "CREA-SC 12345",
            "processPrefix": "PA-IPUF-2026/",
        },
        "location": {
            "city": "Florianópolis, SC",
            "corridor": "Avenida Beira-Mar Norte",
            "zone": "Zona Central",
            "jurisdiction": "Municipal (IPUF / PMF)",
            "controlledIntersections": 12,
            "corridorsMonitored": 2,
        },
        "safetyInterventions": ["Intervenção Teste A", "Intervenção Teste B"],
        "defaultSensors": [
            {
                "id": "DET-SC-01",
                "junction": "Av. Beira-Mar Norte x R. Bocaiúva",
                "measuredSpeed": 45.0,
                "flowRate": 1500,
                "occupancyRate": 60.0,
                "saturationDegree": 0.70,
                "status": "NORMAL",
                "queueLengthMeters": 35.0,
            }
        ],
        "quesitos": [
            {
                "id": "Q-CUSTOM-01",
                "question": "O sistema customizado operou em conformidade com o plano semafórico?",
                "referenceRule": "Portaria Municipal nº 01/2026",
                "technicalJustification": "Operação em conformidade com as regras de sincronismo e onda verde.",
                "answer": "SIM",
            }
        ],
        "legalFraming": [
            {
                "article": "Art. 1º do Decreto Municipal",
                "description": "Regulamentação de teste municipal.",
                "technicalEvidence": "Telemetria auditada.",
            }
        ],
    }

    template_file = tmp_path / "custom_template.json"
    template_file.write_text(json.dumps(custom_template), encoding="utf-8")

    service = TrafficReportService(template_path=str(template_file))
    output = service.build_report()
    report = output["report"]

    assert report["system"] == "SYNAPSE Custom v9.9"
    assert report["auditObjective"] == "Auditoria Experimental Personalizada."
    assert report["cityHall"] == "PREFEITURA DE FLORIANÓPOLIS"
    assert report["location"]["corridor"] == "Avenida Beira-Mar Norte"
    assert len(report["quesitos"]) == 1
    assert report["quesitos"][0]["id"] == "Q-CUSTOM-01"


def test_traffic_report_service_missing_template_fallback():
    service = TrafficReportService(template_path="/non/existent/path/template_9999.json")
    output = service.build_report()
    assert "report" in output
    assert "formatted_markdown" in output
    assert output["report"]["system"] == "SYNAPSE Core v2.0 Enterprise"

