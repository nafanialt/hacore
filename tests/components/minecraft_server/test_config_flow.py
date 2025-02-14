"""Test the Minecraft Server config flow."""

from unittest.mock import AsyncMock, patch

import aiodns
from mcstatus.status_response import JavaStatusResponse

from homeassistant.components.minecraft_server.const import (
    DEFAULT_NAME,
    DEFAULT_PORT,
    DOMAIN,
)
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType


class QueryMock:
    """Mock for result of aiodns.DNSResolver.query."""

    def __init__(self) -> None:
        """Set up query result mock."""
        self.host = "mc.dummyserver.com"
        self.port = 23456
        self.priority = 1
        self.weight = 1
        self.ttl = None


JAVA_STATUS_RESPONSE_RAW = {
    "description": {"text": "Dummy Description"},
    "version": {"name": "Dummy Version", "protocol": 123},
    "players": {
        "online": 3,
        "max": 10,
        "sample": [
            {"name": "Player 1", "id": "1"},
            {"name": "Player 2", "id": "2"},
            {"name": "Player 3", "id": "3"},
        ],
    },
}

USER_INPUT = {
    CONF_NAME: DEFAULT_NAME,
    CONF_HOST: f"mc.dummyserver.com:{DEFAULT_PORT}",
}

USER_INPUT_SRV = {CONF_NAME: DEFAULT_NAME, CONF_HOST: "dummyserver.com"}

USER_INPUT_IPV4 = {
    CONF_NAME: DEFAULT_NAME,
    CONF_HOST: f"1.1.1.1:{DEFAULT_PORT}",
}

USER_INPUT_IPV6 = {
    CONF_NAME: DEFAULT_NAME,
    CONF_HOST: f"[::ffff:0101:0101]:{DEFAULT_PORT}",
}

USER_INPUT_PORT_TOO_SMALL = {
    CONF_NAME: DEFAULT_NAME,
    CONF_HOST: "mc.dummyserver.com:1023",
}

USER_INPUT_PORT_TOO_LARGE = {
    CONF_NAME: DEFAULT_NAME,
    CONF_HOST: "mc.dummyserver.com:65536",
}


async def test_show_config_form(hass: HomeAssistant) -> None:
    """Test if initial configuration form is shown."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_port_too_small(hass: HomeAssistant) -> None:
    """Test error in case of a too small port."""
    with patch(
        "aiodns.DNSResolver.query",
        side_effect=aiodns.error.DNSError,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=USER_INPUT_PORT_TOO_SMALL
        )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "invalid_port"}


async def test_port_too_large(hass: HomeAssistant) -> None:
    """Test error in case of a too large port."""
    with patch(
        "aiodns.DNSResolver.query",
        side_effect=aiodns.error.DNSError,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=USER_INPUT_PORT_TOO_LARGE
        )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "invalid_port"}


async def test_connection_failed(hass: HomeAssistant) -> None:
    """Test error in case of a failed connection."""
    with patch(
        "aiodns.DNSResolver.query",
        side_effect=aiodns.error.DNSError,
    ), patch("mcstatus.server.JavaServer.async_status", side_effect=OSError):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=USER_INPUT
        )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "cannot_connect"}


async def test_connection_succeeded_with_srv_record(hass: HomeAssistant) -> None:
    """Test config entry in case of a successful connection with a SRV record."""
    with patch(
        "aiodns.DNSResolver.query",
        side_effect=AsyncMock(return_value=[QueryMock()]),
    ), patch(
        "mcstatus.server.JavaServer.async_status",
        return_value=JavaStatusResponse(
            None, None, None, None, JAVA_STATUS_RESPONSE_RAW, None
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=USER_INPUT_SRV
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == USER_INPUT_SRV[CONF_HOST]
        assert result["data"][CONF_NAME] == USER_INPUT_SRV[CONF_NAME]
        assert result["data"][CONF_HOST] == USER_INPUT_SRV[CONF_HOST]


async def test_connection_succeeded_with_host(hass: HomeAssistant) -> None:
    """Test config entry in case of a successful connection with a host name."""
    with patch(
        "aiodns.DNSResolver.query",
        side_effect=aiodns.error.DNSError,
    ), patch(
        "mcstatus.server.JavaServer.async_status",
        return_value=JavaStatusResponse(
            None, None, None, None, JAVA_STATUS_RESPONSE_RAW, None
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=USER_INPUT
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == USER_INPUT[CONF_HOST]
        assert result["data"][CONF_NAME] == USER_INPUT[CONF_NAME]
        assert result["data"][CONF_HOST] == "mc.dummyserver.com"


async def test_connection_succeeded_with_ip4(hass: HomeAssistant) -> None:
    """Test config entry in case of a successful connection with an IPv4 address."""
    with patch("getmac.get_mac_address", return_value="01:23:45:67:89:ab"), patch(
        "aiodns.DNSResolver.query",
        side_effect=aiodns.error.DNSError,
    ), patch(
        "mcstatus.server.JavaServer.async_status",
        return_value=JavaStatusResponse(
            None, None, None, None, JAVA_STATUS_RESPONSE_RAW, None
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=USER_INPUT_IPV4
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == USER_INPUT_IPV4[CONF_HOST]
        assert result["data"][CONF_NAME] == USER_INPUT_IPV4[CONF_NAME]
        assert result["data"][CONF_HOST] == "1.1.1.1"


async def test_connection_succeeded_with_ip6(hass: HomeAssistant) -> None:
    """Test config entry in case of a successful connection with an IPv6 address."""
    with patch("getmac.get_mac_address", return_value="01:23:45:67:89:ab"), patch(
        "aiodns.DNSResolver.query",
        side_effect=aiodns.error.DNSError,
    ), patch(
        "mcstatus.server.JavaServer.async_status",
        return_value=JavaStatusResponse(
            None, None, None, None, JAVA_STATUS_RESPONSE_RAW, None
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=USER_INPUT_IPV6
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == USER_INPUT_IPV6[CONF_HOST]
        assert result["data"][CONF_NAME] == USER_INPUT_IPV6[CONF_NAME]
        assert result["data"][CONF_HOST] == "::ffff:0101:0101"
