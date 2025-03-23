from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from pydantic import BaseModel, Field
from typing import List

class Company(BaseModel):
    name: str = Field(description="Company name")
    ticker: str = Field(description="Stock ticker symbol")
    reason: str = Field(description="Reason this company is newsworthy")

class MarketWatchOutput(BaseModel):
    companies: List[Company] = Field(description="List of 3 newsworthy companies")

class CompanyAnalysis(BaseModel):
    company: Company = Field(description="Company information")
    financial_analysis: str = Field(description="Financial analysis of the company")
    market_position: str = Field(description="Current market position and competitive analysis")
    future_outlook: str = Field(description="Future outlook and growth prospects")
    investment_potential: str = Field(description="Investment potential and suitability for investment")


@CrewBase
class StockPicker():
    """StockPicker crew"""

    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    # Track company analyses
    company_analyses = []

    @agent
    def market_watcher(self) -> Agent:
        return Agent(config=self.agents_config['market_watcher'])
    
    @agent
    def researcher(self) -> Agent:
        return Agent(config=self.agents_config['researcher'])

    @agent
    def analyst(self) -> Agent:
        return Agent(config=self.agents_config['analyst'])
    
    @task
    def market_watch_task(self) -> Task:
        return Task(
            config=self.tasks_config['market_watch_task'],
            output_schema=MarketWatchOutput,
            callback=self.create_research_tasks
        )

    def create_research_tasks(self, output):
        """Callback to dynamically create research tasks for each company"""
        if not isinstance(output, MarketWatchOutput):
            # Handle the case where output isn't properly structured
            return
        
        self.company_analyses = []
        research_tasks = []
        
        # Create a research task for each company
        for company in output.companies:
            research_task = Task(
                description=f"Thorough research on company: {company.name} ({company.ticker}) focusing on current news, financial health and investment potential",
                expected_output=f"Detailed analysis of {company.name} and suitability for investment",
                agent=self.researcher,
                output_schema=CompanyAnalysis,
                context=company.model_dump_json(),
                callback=self.store_company_analysis
            )
            research_tasks.append(research_task)
        
        # Return the dynamically created tasks
        return research_tasks
    
    def store_company_analysis(self, output, task):
        """Store each company analysis as it's completed"""
        self.company_analyses.append(output)


    @task
    def analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config['analysis_task'],
            dependencies=[self.market_watch_task],
            output_file='report.md',
            context=self.company_analyses
        )

    @crew
    def crew(self) -> Crew:
        """Creates the StockPicker crew"""

        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
