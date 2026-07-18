"""HEP-native tools exposed to the agent as an in-process MCP server."""

from fisicai.tools.arxiv import TOOLS as ARXIV_TOOLS
from fisicai.tools.hepdata import TOOLS as HEPDATA_TOOLS
from fisicai.tools.inspire import TOOLS as INSPIRE_TOOLS
from fisicai.tools.pyhf_tools import TOOLS as PYHF_TOOLS

ALL_TOOLS = [*INSPIRE_TOOLS, *ARXIV_TOOLS, *HEPDATA_TOOLS, *PYHF_TOOLS]
