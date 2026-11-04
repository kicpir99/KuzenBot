from dataclasses import dataclass, field

@dataclass
class SmiteBuild:
    title: str
    patch: str
    is_aspect: bool
    roles: list[str] = field(default_factory=list)  # np. ['Mid'], ['Carry', 'Mid', 'Solo']
    starter_items: list[str] = field(default_factory=list)
    final_items: list[str] = field(default_factory=list)
    relics: list[str] = field(default_factory=list)
    consumables: list[str] = field(default_factory=list)
    swap_items: list[dict] = field(default_factory=list) # [{'from': 'A', 'to': 'B', 'reason': 'Why'}]
    build_url: str = ""
    upvotes: int = 0
    author: str = "Unknown"
    is_partner: bool = False
    ability_priority: list[str] = field(default_factory=list)
    ability_details: dict = field(default_factory=dict) # {"1": {"name": "...", "img": "..."}}
    is_stats: bool = False
    stats_data: dict = field(default_factory=dict)
    insufficient_data: bool = False
    tier: str = ""              # np. "A+", "S", "B"
    win_rate: str = ""          # np. "56%"
    wins: int = 0
    losses: int = 0
    total_matches: int = 0      # matchEvidenceGames
    cost: int = 0               # łączny koszt w goldzie

    def is_valid(self) -> bool:
        """Returns True if the build has all required data for display."""
        if self.title is None:
            return False
        
        if getattr(self, 'insufficient_data', False):
            return True
        
        # Jeśli build nie ma żadnych przedmiotów (finalnych ani starterów), to raczej bezużyteczny
        if not self.final_items and not self.starter_items:
            return False
            
        return True

@dataclass
class GodData:
    god_name: str
    current_patch: str
    builds: list[SmiteBuild] = field(default_factory=list)
    error: str = None
