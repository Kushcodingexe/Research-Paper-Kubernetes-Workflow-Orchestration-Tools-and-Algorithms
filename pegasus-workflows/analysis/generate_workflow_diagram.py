#!/usr/bin/env python3
"""
Generate Pegasus Workflow Visualization
Creates HTML/SVG diagram of the Montage-pattern rack resiliency workflow.
"""

import os

def generate_mermaid_diagram(scale='1x'):
    """Generate Mermaid diagram for the workflow."""
    configs = {
        '1x': {'hc': 3, 'ns': 1, 'ic': 1, 'rs': 1, 'fc': 1},
        '2x': {'hc': 6, 'ns': 2, 'ic': 2, 'rs': 2, 'fc': 2},
        '4x': {'hc': 12, 'ns': 4, 'ic': 4, 'rs': 4, 'fc': 4},
    }
    cfg = configs.get(scale, configs['1x'])
    
    mermaid = f"""flowchart TD
    subgraph Stage1["Stage 1: Health Checks (mProjectPP)"]
"""
    # Health checks
    for i in range(1, cfg['hc'] + 1):
        mermaid += f"        HC{i}[Health Check {i}]\n"
    
    mermaid += """    end
    
    subgraph Stage2["Stage 2: Node Failure Sim (mDiff)"]
"""
    # Node sims
    for i in range(1, cfg['ns'] + 1):
        mermaid += f"        NS{i}[Node Sim {i}]\n"
    
    mermaid += """    end
    
    subgraph Stage3["Stage 3: Interim Health Check (mFitPlane)"]
"""
    # Interim checks
    for i in range(1, cfg['ic'] + 1):
        mermaid += f"        IC{i}[Interim Check {i}]\n"
    
    mermaid += """    end
    
    subgraph Stage4["Stage 4: Rack Failure Sim (mBackground)"]
"""
    # Rack sims
    for i in range(1, cfg['rs'] + 1):
        mermaid += f"        RS{i}[Rack Sim {i}]\n"
    
    mermaid += """    end
    
    subgraph Stage5["Stage 5: Final Health Check (mImgtbl)"]
"""
    # Final checks
    for i in range(1, cfg['fc'] + 1):
        mermaid += f"        FC{i}[Final Check {i}]\n"
    
    mermaid += "    end\n\n"
    
    # Dependencies: HC -> NS
    for hc in range(1, cfg['hc'] + 1):
        for ns in range(1, cfg['ns'] + 1):
            mermaid += f"    HC{hc} --> NS{ns}\n"
    
    # NS -> IC
    for ns in range(1, cfg['ns'] + 1):
        for ic in range(1, cfg['ic'] + 1):
            mermaid += f"    NS{ns} --> IC{ic}\n"
    
    # IC -> RS
    for ic in range(1, cfg['ic'] + 1):
        for rs in range(1, cfg['rs'] + 1):
            mermaid += f"    IC{ic} --> RS{rs}\n"
    
    # RS -> FC
    for rs in range(1, cfg['rs'] + 1):
        for fc in range(1, cfg['fc'] + 1):
            mermaid += f"    RS{rs} --> FC{fc}\n"
    
    return mermaid


def generate_html_visualization(output_dir='/app/output'):
    """Generate complete HTML visualization with all scales."""
    
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Pegasus Rack Resiliency Workflow - Montage Pattern</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <style>
        body { 
            font-family: 'Segoe UI', Arial, sans-serif; 
            margin: 20px; 
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            min-height: 100vh;
        }
        h1 { 
            text-align: center; 
            color: #00d4ff;
            text-shadow: 0 0 10px rgba(0,212,255,0.5);
        }
        h2 { color: #ff6b6b; margin-top: 30px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .diagram { 
            background: rgba(255,255,255,0.05); 
            padding: 20px; 
            border-radius: 15px; 
            margin: 20px 0;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .mermaid { text-align: center; }
        .stats { 
            display: grid; 
            grid-template-columns: repeat(3, 1fr); 
            gap: 20px; 
            margin: 30px 0;
        }
        .stat-card {
            background: linear-gradient(135deg, rgba(0,212,255,0.2), rgba(255,107,107,0.2));
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.2);
        }
        .stat-value { font-size: 2em; font-weight: bold; color: #00d4ff; }
        .stat-label { color: #aaa; }
        table { 
            width: 100%; 
            border-collapse: collapse; 
            margin: 20px 0;
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
            overflow: hidden;
        }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.1); }
        th { background: rgba(0,212,255,0.2); color: #00d4ff; }
        tr:hover { background: rgba(255,255,255,0.05); }
        .legend { margin: 20px 0; padding: 15px; background: rgba(255,255,255,0.05); border-radius: 10px; }
        .legend span { margin-right: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Pegasus Rack Resiliency Workflow</h1>
        <h2>Montage Pattern Mapping</h2>
        
        <div class="legend">
            <strong>Montage Pattern Stages:</strong><br>
            <span>📊 mProjectPP → Health Checks</span>
            <span>🔄 mDiff → Node Failure Sim</span>
            <span>📈 mFitPlane → Interim Check</span>
            <span>⚙️ mBackground → Rack Failure Sim</span>
            <span>📋 mImgtbl → Final Check</span>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">7</div>
                <div class="stat-label">Jobs (1x Scale)</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">14</div>
                <div class="stat-label">Jobs (2x Scale)</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">28</div>
                <div class="stat-label">Jobs (4x Scale)</div>
            </div>
        </div>
        
        <h2>1x Scale Workflow (7 Jobs)</h2>
        <div class="diagram">
            <div class="mermaid">
""" + generate_mermaid_diagram('1x') + """
            </div>
        </div>
        
        <h2>2x Scale Workflow (14 Jobs)</h2>
        <div class="diagram">
            <div class="mermaid">
""" + generate_mermaid_diagram('2x') + """
            </div>
        </div>
        
        <h2>Benchmark Results</h2>
        <table>
            <tr>
                <th>Scale</th>
                <th>Total Jobs</th>
                <th>Mean Duration</th>
                <th>Std Dev</th>
                <th>Min</th>
                <th>Max</th>
                <th>Scaling Efficiency</th>
            </tr>
            <tr>
                <td>1x</td>
                <td>7</td>
                <td>143.45s</td>
                <td>16.68s</td>
                <td>130s</td>
                <td>189s</td>
                <td>100% (baseline)</td>
            </tr>
            <tr>
                <td>2x</td>
                <td>14</td>
                <td>165.95s</td>
                <td>13.68s</td>
                <td>144s</td>
                <td>204s</td>
                <td>173% (2x jobs in 1.16x time)</td>
            </tr>
            <tr>
                <td>4x</td>
                <td>28</td>
                <td>174.30s</td>
                <td>15.95s</td>
                <td>159s</td>
                <td>220s</td>
                <td>328% (4x jobs in 1.22x time)</td>
            </tr>
        </table>
        
        <h2>Key Observations</h2>
        <ul>
            <li>✅ <strong>Excellent Parallel Scaling:</strong> 4x workload completes in only 22% more time</li>
            <li>✅ <strong>Consistent Performance:</strong> Low standard deviation across all scales</li>
            <li>✅ <strong>HTCondor Efficiency:</strong> Local universe execution minimizes overhead</li>
        </ul>
    </div>
    
    <script>
        mermaid.initialize({ 
            startOnLoad: true,
            theme: 'dark',
            flowchart: { curve: 'basis' }
        });
    </script>
</body>
</html>
"""
    
    output_path = os.path.join(output_dir, 'pegasus_workflow_visualization.html')
    with open(output_path, 'w') as f:
        f.write(html)
    print(f"Visualization saved to: {output_path}")
    return output_path


if __name__ == '__main__':
    import sys
    output_dir = sys.argv[1] if len(sys.argv) > 1 else '/app/output'
    generate_html_visualization(output_dir)
