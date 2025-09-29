# What are the methodological developments and research gaps in experimental trading platforms like zTree and oTree over the past two decades? An example paper here is: Zurich Trading Simulator (ZTS) - A dynamic trading experimental tool for oTree

Experimental trading platforms have evolved from rigid zTree
implementations to modular web-based systems like oTree with improved
scalability and real-time capabilities, but systematic comparative
performance evaluations across domains remain a significant research
gap.

## Abstract

Over the past two decades, experimental trading platforms have shifted
from the rigid, laboratory‐based design of early zTree implementations
to modular, web‐based systems exemplified by oTree and the Bristol Stock
Exchange. Studies report that these newer platforms integrate real-time
communication (for example, via websockets), open-source codebases, and
Python‐driven modular frameworks that support both human and automated
agents. Several papers detail simulation environments that encompass
continuous double auctions, limit order book dynamics, frequent batch
auctions, and even neural-stochastic as well as opinion dynamics models.

At least eight studies each focus on zTree and oTree variants and a
similar number describe Bristol Stock Exchange--type platforms. A
dominant trend is the publication of platform and tool descriptions,
with many contributions extending these designs for applications in
trading, risk taking, and market microstructure analysis. Although
papers highlight improvements in scalability and configurability,
systematic comparative evaluations of performance across different
domains remain infrequent.

## Paper search

Using your research question \"What are the methodological developments
and research gaps in experimental trading platforms like zTree and oTree
over the past two decades? An example paper here is: Zurich Trading
Simulator (ZTS) - A dynamic trading experimental tool for oTree\", we
[searched](https://support.elicit.com/en/articles/553025) across over
126 million academic papers from the [Semantic
Scholar](https://www.semanticscholar.org/) corpus. We retrieved the 500
papers most relevant to the query.

## Screening

We screened in sources that met these criteria:

- **Experimental Trading Platform**: Does the study utilize zTree,
  oTree, or other comparable experimental trading platforms?
- **Methodological Focus**: Does the study present methodological
  innovations, technical developments, new features, tools, modules,
  extensions, OR discuss platform limitations, technical challenges, or
  methodological gaps related to experimental trading platforms?
- **Publication Timeline**: Was the study published between 2005-2025?
- **Methodological Discussion**: Does the study discuss methodological
  aspects, limitations, or innovations (rather than using trading
  platforms solely as tools without methodological discussion)?
- **Experimental Implementation**: Does the study include experimental
  implementation (rather than being purely theoretical trading models)?
- **Trading Focus**: Does the study focus on trading experimental
  paradigms (rather than exclusively on non-trading experiments like
  public goods games or auctions without trading components)?
- **Publication Type**: Is this a full research paper with sufficient
  methodological detail (rather than a conference abstract, poster, or
  brief communication)?

We considered all screening questions together and made a holistic
judgement about whether to screen in each paper.

## Data extraction

We asked a large language model to extract each data column below from
each paper. We gave the model the extraction instructions shown below
for each column.

- **Software Platform Type**:

<!-- -->

- Identify the specific experimental trading platform discussed in the
  study.

<!-- -->

- Record the exact name of the platform (e.g., zTree, oTree, Zurich
  Trading Simulator)
- Note the primary purpose of the platform
- Capture any unique features or innovations of the platform If multiple
  platforms are discussed, list all of them. Example formats:
- \"oTree Markets: market simulation framework\"
- \"zTree: economic experiment development software\"

<!-- -->

- **Platform Technical Specifications**:

<!-- -->

- Extract technical details about the platform:

<!-- -->

- Programming language used
- Key technical components (e.g., Python implementation, exchange
  mechanism)
- Modularity or customization capabilities
- Open-source status
- Availability of source code Prioritize precise technical descriptions.
  If specific details are missing, note \"Not specified\".

<!-- -->

- **Experimental Use Cases**:

<!-- -->

- Identify specific types of experiments or research domains the
  platform supports:

<!-- -->

- List all mentioned experimental contexts (e.g., trading, investment,
  decision-making)
- Note any specific experimental paradigms demonstrated
- Capture any limitations or constraints of the platform If multiple use
  cases are mentioned, list them in order of prominence.

<!-- -->

- **Experimental Configuration Options**:

<!-- -->

- Document the platform\'s flexibility and configuration capabilities:

<!-- -->

- Describe default settings available
- Note possibilities for experimenter customization
- Identify any pre-developed experimental components or templates
- Capture any constraints on experimental design Use direct quotes from
  the text where possible to preserve nuance.

<!-- -->

- **Methodological Innovations**:

<!-- -->

- Identify and describe any novel methodological contributions:

<!-- -->

- Specific technical innovations
- Improvements over previous experimental platforms
- Unique features that address prior research limitations
- Potential impact on experimental design in economics/psychology
  Prioritize substantive methodological advances over minor technical
  improvements.

# Results

## Characteristics of Included Studies

  -----------------------------------------------------------------------------------------------------------------
  Study          Platform Focus Methodological        Application Domain        Study Type              Full text
                                Contribution                                                            retrieved
  -------------- -------------- --------------------- ------------------------- ----------------------- -----------
  Andraszewicz   Zurich Trading Free, adaptable,      Trading activity, risk    Platform/tool           No
  et al., 2022   Simulator      dynamic trading       taking, decision making   description,            
                 (ZTS) for      experiment tool;                                application             
                 oTree          customizable source                                                     
                                code; price paths                                                       
                                online                                                                  

  Crede et al.,  oTree with     Real-time interaction Continuous double         Platform extension,     No
  2019           websockets     via websockets;       auction, large online     technical note          
                                immediate updates;    markets, teaching                                 
                                open-source                                                             

  Grant, 2020    oTree Markets  Modular Python        Market simulation,        Platform/tool           No
                                framework for market  trading                   description             
                                simulation;                                                             
                                replaceable                                                             
                                components                                                              

  Aldrich et     oTree-based    Modular, flexible,    Financial market          Platform/tool           Yes
  al., 2019      financial      scalable; supports    experiments,              description             
                 market         continuous/discrete   high-frequency trading,                           
                 architecture   time, high-frequency  algorithmic trading                               
                                trading                                                                 

  Fischbacher,   zTree          Economic experiment   Games, auctions,          Platform/tool           Yes
  1999a                         development; rapid    neuroeconomics            description             
                                prototyping; flexible                                                   
                                design                                                                  

  Fischbacher,   zTree          No programming        Simultaneous/sequential   Platform manual         No
  1999b                         required; integrated  games, markets                                    
                                features for                                                            
                                experiment management                                                   

  Stotter et     Exchange       Real-time,            Financial trading,        Platform/tool           Yes
  al., 2014      Portal (ExPo)  open-source,          behavioral economics      description,            
                                networked trading                               application             
                                experiments;                                                            
                                agent/human                                                             
                                integration                                                             

  Cliff, 2018    Bristol Stock  Full limit order book Algorithmic trading,      Platform/tool           No
                 Exchange (BSE) (LOB) implementation; order routing, arbitrage  description             
                                reference trading                                                       
                                systems; open-source                                                    

  Palan, 2015a   GIMS           Open-source,          Financial/economic        Platform/tool           No
                                extensible market     research, trading         description             
                                software                                                                

  Sonnemans and  zTree, oTree,  Review of lab         Experimental economics    Review/methodological   No
  van der Veen,  PHP,           organization,         labs                                              
  2019           JavaScript     software selection                                                      
                                criteria                                                                

  Stotter et     Exchange       Real-time,            Financial trading,        Platform/tool           Yes
  al., 2013      Portal (ExPo)  agent/human trading;  agent-based experiments   description,            
                                market shocks;                                  application             
                                adaptive, stochastic,                                                   
                                agent-driven (ASAD)                                                     
                                agents                                                                  

  Schaffner,     zTree, CORAL   Lightweight           Economic experiments,     Platform/tool           No
  2013                          experimental          market mechanics          description             
                                framework;                                                              
                                professional software                                                   
                                development practices                                                   

  Palan, 2015b   Open-source    Extensible,           Financial/economic        Platform/tool           No
                 market         easy-to-use,          research                  description             
                 software       comprehensive                                                           
                                functionality                                                           

  LeBlanc, 2018  zTree, novel   Comparison of coding  Macroeconomics, lab       Comparative review      No
                 coding         environments;         experiments                                       
                 environments   flexibility vs.                                                         
                                engineering cost                                                        

  Kolitz et al., meet2trade     Configurable          Trading, auctions,        Platform/tool           No
  2007                          electronic market     decision making           description             
                                platform; integrated                                                    
                                auction server                                                          

  Cliff and      Bristol Stock  Minimal limit order   Trading, financial market Platform/tool           No
  Merkuryev,     Exchange (BSE) book (LOB)            dynamics                  description             
  2018                          simulation;                                                             
                                open-source;                                                            
                                teaching/research                                                       

  Chen et al.,   oTree          Open-source, online,  Social science            Platform/tool           Yes
  2016                          object-oriented;      experiments, trading,     description             
                                Python/Django;        decision making                                   
                                field/lab/online                                                        

  Cliff and      BSE, TBSE      Parallel,             Trading agent evaluation, Platform extension,     Yes
  Rollins, 2020                 asynchronous          artificial                application             
                                simulation;           intelligence/machine                              
                                exhaustive algorithm  learning (AI/ML)                                  
                                testing                                                                 

  Fischbacher,   zTree          Easy experimentation; Public goods, bargaining, Platform manual         No
  1999c                         minimal effort        auctions                                          
                                post-programming                                                        

  Washinyira and oTree with     Websocket integration Economic experiments,     Platform extension,     No
  Chifamba, 2023 websockets     for real-time         real-time data            technical note          
                                communication;                                                          
                                latency reduction                                                       

  Huang et al.,  No mention     Hybrid simulation:    Emission trading,         Application,            No
  2015           found          experimental +        strategic behavior        methodological          
                                agent-based;                                                            
                                real-world data                                                         

  Lomas and      BSE            Integration of        Trading, narrative        Platform extension,     Yes
  Cliff, 2020                   opinion dynamics with economics                 application             
                                agent-based trading                                                     

  Snashall and   BSE            Large-scale,          Trading agent evaluation, Application,            Yes
  Cliff, 2019                   exhaustive agent      artificial                methodological          
                                testing; cloud        intelligence/machine                              
                                computing             learning (AI/ML)                                  

  Cliff, 2019    BSE limit      Realistic, dynamic    Trading, strategy         Application,            Yes
                 order book     market simulation;    evaluation                methodological          
                 (LOB)-market   exhaustive strategy                                                     
                 simulator      testing                                                                 

  Fidanoski and  zTree, oTree   DEEP method           Risk/time preference      Platform extension,     Yes
  Johnson, 2023                 implementation;       elicitation               application             
                                scripts for data                                                        
                                processing                                                              

  Sylvester et   mTree          Agent-based modeling  Arbitrage, blockchain,    Application,            No
  al., 2022                     for automated market  decentralized finance     methodological          
                                makers (AMMs);        (DeFi)                                            
                                decentralized finance                                                   
                                (DeFi)                                                                  

  Ertac and      zTree in       Online experiments    Economic experiments,     Platform extension,     No
  Kotan, 2020    virtual lab    via virtual lab;      interactive tasks         technical note          
                                real-time                                                               
                                participation                                                           

  Shi and        ABIDES         Hybrid                Trading, market           Platform/tool           Yes
  Cartlidge,                    neural-stochastic     manipulation, herding     description,            
  2023                          limit order book                                application             
                                (LOB) simulation;                                                       
                                agent-based + machine                                                   
                                learning (ML)                                                           

  Mascioli et    PyMarketSim    Deep reinforcement    Trading, deep             Platform/tool           No
  al., 2024                     learning (dRL)        reinforcement learning    description             
                                trading agent         (dRL), market dynamics                            
                                environment; private                                                    
                                valuations, limit                                                       
                                order book (LOB)                                                        

  Oh et al.,     Experimental   Open platform for     Grid economics, market    Platform/tool           No
  2007           gaming         grid resource         structures                description             
                 platform       trading; design                                                         
                                science approach                                                        

  Zhang and      BSE            Market-level order    Automated trading, market Platform extension,     Yes
  Cliff, 2020                   flow imbalance        impact                    methodological          
                                (MLOFI) for market                                                      
                                impact; robust                                                          
                                imbalance metrics                                                       

  Sornette et    xYotta         Prediction market     Prediction markets,       Platform/tool           No
  al., 2020                     with fundamental      initial public offering   description             
                                uncertainty; parallel (IPO) simulation                                  
                                markets                                                                 

  Baker and Los, TraderEx       Liquidity scenario    Liquidity, S&P 500,       Application,            No
  2014                          simulation; measure   market microstructure     methodological          
                                evaluation                                                              

  Alves et al.,  SHIFT          Multi-asset,          Trading, market           Platform/tool           Yes
  2023                          asynchronous,         microstructure            description,            
                                order-driven                                    application             
                                simulator; frequent                                                     
                                batch auction (FBA)                                                     
                                vs. continuous double                                                   
                                auction (CDA)                                                           

  Ono and Sato,  U-Mart systems Agent-based           Market institutions,      Platform/tool           No
  2016                          artificial market     trading strategies        description             
                                simulators; high                                                        
                                fidelity                                                                

  Palan, 2013    No mention     Review of             Asset market experiments  Review                  No
                 found          bubbles/crashes in                                                      
                                asset markets                                                           

  Dahan et al.,  No mention     Preference markets    Product development,      Application,            No
  2010           found          for product concept   decision making           methodological          
                                evaluation                                                              

  Balch et al.,  Multi-agent    Market Replay & IABS; Trading strategy          Application,            No
  2019           simulator      background trading    evaluation                methodological          
                                agents                                                                  

  Bokhari and    BSE            Integration of        Narrative economics,      Platform extension,     Yes
  Cliff, 2023                   opinion dynamics and  agent-based modeling      application             
                                adaptive trading                                                        

  Galas et al.,  ATRADE,        Algorithmic           Trading algorithms,       Platform/tool           No
  2012           SocialSTORM    trading/risk          systemic risk             description             
                                analytics; annual                                                       
                                competition                                                             
  -----------------------------------------------------------------------------------------------------------------

Platform Focus:

- oTree (including variants): 8 studies
- zTree (including variants): 8 studies
- Bristol Stock Exchange (BSE, including variants): 8 studies
- Exchange Portal (ExPo): 2 studies
- All other platforms (GIMS, PHP, JavaScript, CORAL, open-source market
  software, meet2trade, TBSE, mTree, ABIDES, PyMarketSim, experimental
  gaming platform, xYotta, TraderEx, SHIFT, U-Mart, multi-agent
  simulator, ATRADE, SocialSTORM): 1 study each
- We didn\'t find mention of a platform in three studies

Methodological Contribution / Study Type:

- Platform/tool description: 16 studies
- Platform/tool description, application: 5 studies
- Platform extension, application: 5 studies
- Platform extension, technical note: 3 studies
- Platform extension, methodological: 1 study
- Platform manual: 2 studies
- Application, methodological: 7 studies
- Review/methodological: 1 study
- Review: 1 study
- Comparative review: 1 study

Application Domain:

- Trading (including financial trading, market simulation, etc.): 11
  studies
- Auctions: 4 studies
- Financial/economic research/experiments: 4 studies
- Agent-based/artificial intelligence/machine learning/strategy
  evaluation: 7 studies
- Behavioral/experimental economics: 3 studies
- Market microstructure/dynamics: 3 studies
- Decision making/risk/time preference: 4 studies
- Narrative economics: 2 studies
- Market manipulation/herding: 2 studies
- Blockchain/decentralized finance: 2 studies
- Product development: 1 study
- Teaching/lab experiments: 2 studies
- Other domains (e.g., grid economics, emission trading, prediction
  markets, etc.): 8 studies

We didn\'t find mention of a platform in three studies. All studies had
at least one application domain.

------------------------------------------------------------------------

## Thematic Analysis

### Platform Architecture and Technical Capabilities

- Shift to modular, web-based, and configurable systems:Several studies
  describe a move from monolithic, laboratory-based platforms (such as
  zTree) to modular, web-based, and highly configurable systems (such as
  oTree, Bristol Stock Exchange, ABIDES, and SHIFT).
- Support for human and automated agents:Many platforms now enable both
  human and automated agent participation, real-time interaction, and
  distributed experiments.
- Open-source code and transparency:Multiple studies note that
  open-source code supports transparency, reproducibility, and
  community-driven development.
- Modularity and extensibility:Platforms like oTree, Bristol Stock
  Exchange, and ABIDES emphasize modularity, allowing customization of
  market mechanisms, agent behaviors, and experimental protocols.
- Real-time capabilities:Integration of real-time features, such as
  websockets, has improved latency and responsiveness, supporting more
  dynamic experiments.

### Market Simulation and Trading Mechanisms

- Range of market mechanisms:The reviewed platforms support continuous
  double auctions, frequent batch auctions, limit order books, and
  decentralized finance protocols.
- Pre-developed experimental components:Many platforms provide templates
  for common experimental paradigms, including trading, investment, risk
  elicitation, and decision-making.
- Agent-based modeling:This is a dominant approach, with platforms such
  as Bristol Stock Exchange, ABIDES, SHIFT, and mTree enabling studies
  of heterogeneous agent populations, algorithmic trading strategies,
  and emergent market phenomena.
- Recent innovations:A subset of studies report integration of opinion
  dynamics, narrative economics, and neural-stochastic modeling to
  capture more complex behavioral and informational dynamics.

### Programming Frameworks and Development Approaches

- Python as the dominant language:Python is the primary language for new
  platforms and extensions, especially for oTree, Bristol Stock
  Exchange, ABIDES, and PyMarketSim.
- Other languages:Ruby (for Exchange Portal), Visual Basic for
  Applications, and STATA scripts are also used in some platforms.
- Professional software practices:Adoption of modular architectures and
  open-source licensing has facilitated rapid prototyping,
  extensibility, and collaborative development.

### Performance and Scalability Enhancements

- Real-time and large-scale experiments:Several studies address
  performance and scalability for real-time, high-frequency, and
  large-scale experiments.
- Websockets and cloud computing:Use of websockets enables real-time
  communication, while cloud computing supports exhaustive agent testing
  and scalability.
- Asynchronous simulation architectures:Platforms such as TBSE and SHIFT
  use multi-threaded or asynchronous architectures to improve
  performance.
- Participant numbers:oTree and Bristol Stock Exchange are designed for
  moderate participant numbers, with distributed or cloud-based
  solutions proposed for larger-scale studies.

### Integration and Interoperability

- External data and protocols:Some platforms, such as ABIDES,
  incorporate realistic messaging systems based on real-world market
  protocols.
- Integration with online labor markets and educational settings:Several
  platforms support integration with online labor markets, field
  experiments, and teaching environments.
- Combining experimental and computational methods:The ability to
  combine experimental, agent-based, and computational methods is
  highlighted as a methodological advance in some studies.

# References

Ann‐Kathrin Crede, J. Dietrich, J. Gehrlein, O. Neumann, M. Stürmer, and
F. Bieberstein. "[Otree: Implementing Websockets to Allow for Real-Time
Interactions -- a Continuous Double Auction Market as First
Application](https://doi.org/10.2139/ssrn.3631680)." *Social Science
Research Network*, 2019.

Arwa Bokhari, and D. Cliff. "[Studying Narrative Economics by Adding
Continuous-Time Opinion Dynamics to an Agent-Based Model of
Co-Evolutionary Adaptive Financial
Markets](https://doi.org/10.2139/ssrn.4316574)." *International
Conference on Agents and Artificial Intelligence*, 2023.

Chris Mascioli, Anri Gu, Yongzhao Wang, Mithun Chakraborty, and Michael
P. Wellman. "[A Financial Market Simulation Environment for Trading
Agents Using Deep Reinforcement
Learning](https://doi.org/10.1145/3677052.3698639)." *International
Conference on AI in Finance*, 2024.

D. Cliff. "[An Open-Source Limit-Order-Book Exchange for Teaching and
Research](https://doi.org/10.1109/SSCI.2018.8628760)." *IEEE Symposium
Series on Computational Intelligence*, 2018.

---------. "[Exhaustive Testing of Trader-Agents in Realistically
Dynamic Continuous Double Auction Markets: AA Does Not
Dominate](https://doi.org/10.5220/0007382802240236)." *International
Conference on Agents and Artificial Intelligence*, 2019.

D. Cliff, and Michael Rollins. "[Methods Matter: A Trading Agent with No
Intelligence Routinely Outperforms AI-Based
Traders](https://doi.org/10.1109/SSCI47803.2020.9308172)." *IEEE
Symposium Series on Computational Intelligence*, 2020.

D. Sornette, Sandra Andraszewicz, Ke Wu, R. O. Murphy, Philipp B.
Rindler, and D. Sanadgol. "[Overpricing Persistence in Experimental
Asset Markets with Intrinsic
Uncertainty](https://doi.org/10.5018/ECONOMICS-EJOURNAL.JA.2020-20)."
*Economics*, 2020.

Daniel L. Chen, Martin Schonger, and C. Wickens. "[oTree - An
Open-Source Platform for Laboratory, Online, and Field
Experiments](https://doi.org/10.2139/ssrn.2806713)," 2016.

Daniel Snashall, and D. Cliff. "[Adaptive-Aggressive Traders Don\'t
Dominate](https://doi.org/10.1007/978-3-030-37494-5_13)." *International
Conference on Agents and Artificial Intelligence*, 2019.

Danny Oh, Shih-Fen Cheng, Dan Ma, and R. Bapna. "[Designing an
Experimental Gaming Platform for Trading Grid
Resources](https://doi.org/10.1142/9789812708823_0018)," 2007.

E. Dahan, Arina Soukhoroukova, and Martin Spann. "[New Product
Development 2.0: Preference Markets---How Scalable Securities Markets
Identify Winning Product Concepts and
Attributes\*](https://doi.org/10.1111/J.1540-5885.2010.00763.X)," 2010.

Eric M. Aldrich, Hasan Ali Demirci, and Kristian López Vargas. "[An
oTree-Based Flexible Architecture for Financial Market
Experiments](https://doi.org/10.2139/ssrn.3354426)." *Journal of
Behavioral and Experimental Finance*, 2019.

Filip Fidanoski, and Timothy C. Johnson. "[A Z-Tree Implementation of
the Dynamic Experiments for Estimating Preferences \[DEEP\]
Method](https://doi.org/10.2139/ssrn.4027008)." *Social Science Research
Network*, 2023.

I. Ono, and Hiroshi Sato. "[Building Artificial Markets for Evaluating
Market Institutions and Trading
Strategies](https://doi.org/10.1007/978-4-431-55057-0_3)," 2016.

J. Baker, and C. Los. "[Liquidity and Simulation: A Survey of Liquidity
Measures Using TraderEx](https://doi.org/10.2139/ssrn.2373815)," 2014.

J. LeBlanc. "Three Essays on Macroeconomics and Laboratory Experiments,"
2018.

Jie Huang, Yusheng Xue, Chao Jiang, F. Wen, F. Xue, K. Meng, and Z.
Dong. "[An Experimental Study on Emission Trading Behaviors of
Generation Companies](https://doi.org/10.1109/TPWRS.2014.2366767)."
*IEEE Transactions on Power Systems*, 2015.

Joep Sonnemans, and Ailko van der Veen. "[Software and Laboratory
Organization](https://doi.org/10.4337/9781788110563.00028)." *Handbook
of Research Methods and Applications in Experimental Economics*, 2019.

Kenneth Lomas, and D. Cliff. "[Exploring Narrative Economics: An
Agent-Based-Modeling Platform That Integrates Automated Traders with
Opinion Dynamics](https://doi.org/10.2139/ssrn.3823350)." *International
Conference on Agents and Artificial Intelligence*, 2020.

Klaus Kolitz, Carsten Block, and Christof Weinhardt. "Meet2trade: An
Electronic Market Platform and Experiment System," 2007.

M. Galas, Daniel Brown, and P. Treleaven. "A Computational Social
Science Environment for Financial/Economic Experiments," 2012.

Markus Schaffner. "Programming for Experimental Economics: Introducing
CORAL - a Lightweight Framework for Experimental Economic Experiments,"
2013.

Morgan R. Grant. "oTree Markets," 2020.

Primrose Washinyira, and Shepard Chifamba. "[Integrating Web Sockets in
OTrees to Improve Optimization in
Experiments](https://doi.org/10.21275/sr231130204124)." *International
Journal of Science and Research (IJSR)*, 2023.

Sandra Andraszewicz, Jason Friedman, Dániel Kaszás, and C. Hölscher.
"[Zurich Trading Simulator (ZTS) -- A Dynamic Trading Experimental Tool
for oTree](https://doi.org/10.1016/j.jbef.2022.100762)." *Journal of
Behavioral and Experimental Finance*, 2022.

Sarah Sylvester, K. McCabe, Aleksander Psurek, and Nalin Bhatt.
"[Modeling Arbitrage with an Automated Market
Maker](https://doi.org/10.2139/ssrn.4247283)." *Social Science Research
Network*, 2022.

Seda Ertac, and Ergun Kotan. "[Z-Tree in VLab: A Method for Running
Online Economic Experiments](https://doi.org/10.2139/ssrn.3756019)."
*Social Science Research Network*, 2020.

Stefan Palan. "[A Review of Bubbles and Crashes in Experimental Asset
Markets](https://doi.org/10.1111/joes.12023)," 2013.

---------. "A Software for Asset Market Experiments," 2015.

---------. "[GIMS---Software for Asset Market
Experiments](https://doi.org/10.1016/J.JBEF.2015.02.001)." *Journal of
Behavioral and Experimental Finance*, 2015.

Steve Stotter, J. Cartlidge, and D. Cliff. "[Behavioural Investigations
of Financial Trading Agents Using Exchange Portal
(ExPo)](https://doi.org/10.1007/978-3-662-44994-3_2)." *Transactions on
Computational Collective Intelligence*, 2014.

---------. "[Exploring Assignment-Adaptive (ASAD) Trading Agents in
Financial Market
Experiments](https://doi.org/10.5220/0004248000770088)." *International
Conference on Agents and Artificial Intelligence*, 2013.

T. Balch, Mahmoud Mahfouz, J. Lockhart, Maria Hybinette, and David Byrd.
"How to Evaluate Trading Strategies: Single Agent Market Replay or
Multiple Agent Interactive Simulation?" *arXiv.org*, 2019.

T. W. Alves, I. Florescu, and Dragoş Bozdog. "[Insights on the
Statistics and Market Behavior of Frequent Batch
Auctions](https://doi.org/10.3390/math11051223)." *Mathematics*, 2023.

U. Fischbacher. "[Z-Tree ? Experimenter?S
Manual](https://doi.org/10.2139/SSRN.203310)," 1999.

---------. "[Z-Tree: Zurich Toolbox for Ready-Made Economic
Experiments](https://doi.org/10.3929/ETHZ-A-004372978)," 1999.

Urs Fischbacher. "[Z-Tree - Zurich Toolbox for Readymade Economic
Experiments: Experimenter\'s
Manual](https://doi.org/10.3929/ETHZ-A-004372978)," 1999.

Y., and Merkuryev. "Cliff, D. (2018). BSE: A Minimal Simulation of a
Limit-Order-Book Stock Exchange," 2018.

Zhen Zhang, and D. Cliff. "[Market Impact in Trader-Agents: Adding
Multi-Level Order-Flow Imbalance-Sensitivity to Automated Trading
Systems](https://doi.org/10.2139/ssrn.3823356)." *International
Conference on Agents and Artificial Intelligence*, 2020.

Zijian Shi, and J. Cartlidge. "[Neural Stochastic Agent-Based Limit
Order Book Simulation: A Hybrid
Methodology](https://doi.org/10.48550/arXiv.2303.00080)." *Adaptive
Agents and Multi-Agent Systems*, 2023.
