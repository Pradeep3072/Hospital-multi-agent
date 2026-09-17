import os
import glob
import yaml
import logging
from typing import Dict, List, Optional, Any
from backend.app.profiles.schema import AgentProfileSchema

logger = logging.getLogger(__name__)

PROFILES_DIR = os.path.dirname(os.path.abspath(__file__))
AGENTS_DIR = os.path.join(PROFILES_DIR, "agents")
ETHOS_FILE = os.path.join(PROFILES_DIR, "ETHOS.md")


class NeMoProfileRegistry:
    def __init__(self, agents_dir: str = AGENTS_DIR, ethos_path: str = ETHOS_FILE):
        self.agents_dir = agents_dir
        self.ethos_path = ethos_path
        self.profiles: Dict[str, AgentProfileSchema] = {}
        self.ethos_content: str = ""
        self.load_all()

    def load_all(self):
        """Loads and validates all agent profile YAML files and ETHOS.md."""
        self.profiles.clear()
        
        # Load ETHOS.md
        if os.path.exists(self.ethos_path):
            with open(self.ethos_path, "r", encoding="utf-8") as f:
                self.ethos_content = f.read()
        else:
            self.ethos_content = "# HopeCare Clinical AI Ethos\nPrinciples of safety and non-maleficence."

        # Load YAML profiles
        yaml_files = glob.glob(os.path.join(self.agents_dir, "*.yaml")) + glob.glob(os.path.join(self.agents_dir, "*.yml"))
        for yf in yaml_files:
            try:
                with open(yf, "r", encoding="utf-8") as f:
                    raw_text = f.read()
                    data = yaml.safe_load(raw_text) or {}
                    data["raw_yaml"] = raw_text
                    profile = AgentProfileSchema(**data)
                    self.profiles[profile.name] = profile
            except Exception as e:
                logger.error(f"Error loading agent profile {yf}: {e}")

    def get_profile(self, name: str) -> Optional[AgentProfileSchema]:
        return self.profiles.get(name)

    def list_profiles(self) -> List[AgentProfileSchema]:
        # Return sorted by priority if available
        return sorted(
            list(self.profiles.values()),
            key=lambda p: p.metadata.get("priority", 10)
        )

    def get_ethos(self) -> str:
        return self.ethos_content

    def get_nat_agent_configs(self, llm_name: str = "gemini-2.5-flash") -> Dict[str, Any]:
        """Returns official nvidia-nat AgentBaseConfig objects for each profile."""
        configs = {}
        for name, profile in self.profiles.items():
            nat_cfg = profile.to_nat_agent_config(llm_name=llm_name)
            if nat_cfg:
                configs[name] = nat_cfg
        return configs



# Global singleton registry
profile_registry = NeMoProfileRegistry()
