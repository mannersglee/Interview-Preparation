"""Generate five self-contained, reproducible interview demo notebooks."""
from pathlib import Path
import nbformat as nbf

ROOT = Path(__file__).parent

def make(name, title, intro, sections):
    cells = [nbf.v4.new_markdown_cell(f"# {title}\n\n{intro}\n\n**数据声明**：以下均为固定随机种子生成的模拟数据，不代表真实滴滴业务效果。图中的英文标签用于避免本地中文字体依赖。")]
    for heading, explanation, code in sections:
        cells.append(nbf.v4.new_markdown_cell(f"## {heading}\n\n{explanation}"))
        cells.append(nbf.v4.new_code_cell(code))
    cells.append(nbf.v4.new_markdown_cell("## 实证分析接入\n\n当前目录没有可用于此案例的真实数据，故不把模拟结论解释为实际业务结论。接入真实数据时：①取得脱敏且获授权的数据；②核对数据字典、随机化/触达机制和时间窗；③用真实数据替换模拟数据生成单元；④重跑质量诊断与敏感性分析；⑤在审阅关键识别假设后更新决策摘要。"))
    nb = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec":{"display_name":"Python (myenv)","language":"python","name":"python3"},"language_info":{"name":"python"}})
    nbf.validate(nb)
    nbf.write(nb, ROOT / name)

common = "import numpy as np\nimport pandas as pd\nimport matplotlib.pyplot as plt\nimport seaborn as sns\nfrom scipy import stats\nsns.set_theme(style='whitegrid')\nrng = np.random.default_rng(20261028)"

make('01_补贴策略_AB实验.ipynb', 'Demo 1｜补贴策略 A/B 实验评估',
     '决策问题：补贴能否带来值得付费的增量完单？估计量为用户级 ITT；假设用户间没有显著供给干扰。主指标为实验期人均完单，护栏为取消率和等待时长。', [
    ('设计与模拟数据', '实验前固定 1:1 用户随机分流、双侧 α=0.05、功效 80%。样本量是量级估计，实际需用历史方差和聚类结构校准。数据字典：`arm` 分配；`pre_orders` 实验前订单；`orders` 实验期完单；`cancel` 取消率；`wait` 平均等待分钟；`spend` 补贴元。', common + "\nfrom statsmodels.stats.power import TTestIndPower\nn=6000\npre=rng.poisson(2.0,n)\narm=rng.binomial(1,.5,n)\nsegment=rng.binomial(1,.35,n)\nlam=np.maximum(.1,1.7+.34*pre+.18*segment+.18*arm+.12*arm*segment)\ndf=pd.DataFrame({'user_id':np.arange(n),'arm':arm,'segment':segment,'pre_orders':pre,'orders':rng.poisson(lam),'cancel':rng.binomial(1,np.clip(.11-.006*arm+.004*segment,.01,.9)),'wait':rng.normal(8-.05*arm,1.7,n),'spend':arm*rng.uniform(1.5,2.5,n)})\nprint(df.head())\nprint('Approx. users per arm for MDE 0.20:',round(TTestIndPower().solve_power(effect_size=.20/df.orders.std(),alpha=.05,power=.8)))"),
    ('分流与基线质量检查', '先检查 SRM 和干预前行为平衡。SRM p 值低只提示分流或日志异常，不能证明具体故障。', "count=df.arm.value_counts().sort_index()\nsrm=stats.chisquare(count, f_exp=[n/2,n/2])\nbal=stats.ttest_ind(df.loc[df.arm==1,'pre_orders'],df.loc[df.arm==0,'pre_orders'],equal_var=False)\nprint('Group sizes:',count.to_dict(),'SRM p=',round(srm.pvalue,4),'Baseline p=',round(bal.pvalue,4))\nfig,ax=plt.subplots(1,2,figsize=(11,4))\nsns.countplot(data=df,x='arm',ax=ax[0]);ax[0].set_title('Randomization counts')\nsns.histplot(data=df,x='pre_orders',hue='arm',stat='density',common_norm=False,discrete=True,ax=ax[1]);ax[1].set_title('Pre-period balance')\nplt.tight_layout();plt.show()"),
    ('ITT、CUPED 与业务成本', '按原始分配估计 ITT。CUPED 仅使用干预前变量；系数由全样本协方差估计。比较原始与调整后区间，检查方差是否下降。每增量完单成本用补贴总额除以估计增量订单数；当增量接近零时该比值不稳定。', "def diff_ci(y,a):\n    x1=np.asarray(y)[a==1];x0=np.asarray(y)[a==0]\n    d=x1.mean()-x0.mean();se=np.sqrt(x1.var(ddof=1)/len(x1)+x0.var(ddof=1)/len(x0))\n    return d,se,(d-1.96*se,d+1.96*se)\na=df.arm.to_numpy();raw=diff_ci(df.orders.to_numpy(),a)\ntheta=np.cov(df.orders,df.pre_orders,ddof=1)[0,1]/df.pre_orders.var(ddof=1)\nadj=df.orders-theta*(df.pre_orders-df.pre_orders.mean())\ncuped=diff_ci(adj.to_numpy(),a)\nprint('ITT:',raw,'CUPED:',cuped,'Variance reduction:',1-adj.var()/df.orders.var())\nprint('Subsidy per incremental order:',df.spend.sum()/(raw[0]*(a==1).sum()))\nfig,ax=plt.subplots(1,2,figsize=(11,4))\nfor i,(label,res) in enumerate([('Raw',raw),('CUPED',cuped)]):ax[0].errorbar(res[0],i,xerr=1.96*res[1],fmt='o',capsize=5,label=label)\nax[0].axvline(0,color='black',lw=1);ax[0].set_yticks([0,1],['Raw','CUPED']);ax[0].set_title('Order lift and 95% CI')\ndf.groupby('arm')[['orders','cancel','wait']].mean().T.plot(kind='bar',ax=ax[1]);ax[1].set_title('Primary and guardrails');plt.tight_layout();plt.show()"),
    ('预设分层与决策摘要', '模拟分层仅展示方法，子组结论应看交互项并控制多重检验。上线须同时满足收益大于补贴成本、护栏可接受及无严重干扰。', "rows=[]\nfor s,g in df.groupby('segment'):\n    d,se,ci=diff_ci(g.orders.to_numpy(),g.arm.to_numpy());rows.append((s,d,*ci))\nsub=pd.DataFrame(rows,columns=['segment','lift','low','high']);print(sub)\nplt.figure(figsize=(7,4));plt.errorbar(sub.lift,sub.segment,xerr=[sub.lift-sub.low,sub.high-sub.lift],fmt='o',capsize=5);plt.axvline(0,color='black');plt.yticks([0,1],['existing-like','new-like']);plt.title('Prespecified subgroup effects');plt.show()\nprint('Decision: use estimated lift, cost and guardrails jointly; simulation cannot support a real launch.')")
])

make('02_城市灰度_DiD.ipynb','Demo 2｜城市灰度上线的双重差分评估',
     '决策问题：派单策略是否缩短接驾时长？估计处理城市上线后的 ATT。核心假设是若未上线，处理与对照城市的走势可比。',[
    ('城市周面板与数据字典','`city` 城市；`week` 周；`treated` 是否处理城市；`post` 是否上线后；`wait` 平均接驾分钟。12 城市、24 周，其中 4 城市在第 12 周上线。模拟公共季节性、城市基线和噪声。',common+"\nimport statsmodels.formula.api as smf\ncities=np.arange(12);weeks=np.arange(24);rows=[]\ncity_base=rng.normal(0,.4,12)\nfor c in cities:\n for w in weeks:\n  tr=int(c<4);post=int(w>=12)\n  y=8+city_base[c]+.025*w+.25*np.sin(w/3)-.55*tr*post+rng.normal(0,.16)\n  rows.append((c,w,tr,post,y))\ndf=pd.DataFrame(rows,columns=['city','week','treated','post','wait'])\nprint(df.head())"),
    ('趋势图与前趋势诊断','先看处理与对照组上线前走势，不能只看回归系数。模拟数据的平行趋势是由生成机制设定的；真实数据必须额外论证同期冲击。',"trend=df.groupby(['week','treated']).wait.mean().reset_index()\nplt.figure(figsize=(9,4));sns.lineplot(data=trend,x='week',y='wait',hue='treated',marker='o');plt.axvline(11.5,color='black',ls='--');plt.title('Average pickup time by group');plt.show()\npre=df[df.week<12].copy();pre['time_trend']=pre.week*pre.treated\npre_fit=smf.ols('wait ~ C(city)+C(week)+time_trend',data=pre).fit(cov_type='cluster',cov_kwds={'groups':pre.city})\nprint('Pretrend differential slope:',pre_fit.params['time_trend'],'p=',pre_fit.pvalues['time_trend'])"),
    ('双重差分估计','城市与周固定效应控制稳定城市差异与共同时间冲击；城市聚类标准误考虑城市内相关。但 12 个城市簇偏少，常规聚类区间可能偏乐观，真实研究应考虑更多簇、随机化推断或野生聚类 bootstrap。',"df['did']=df.treated*df.post\nfit=smf.ols('wait ~ did + C(city)+C(week)',data=df).fit(cov_type='cluster',cov_kwds={'groups':df.city})\nprint('DiD ATT:',fit.params['did'],'95% CI:',fit.conf_int().loc['did'].tolist(),'p:',fit.pvalues['did'])\nsummary=df.groupby(['treated','post']).wait.mean().unstack();print(summary)\nfig,ax=plt.subplots(1,2,figsize=(10,4));summary.T.plot(marker='o',ax=ax[0]);ax[0].set_title('Before/after means');ax[1].errorbar(fit.params['did'],0,xerr=1.96*fit.bse['did'],fmt='o',capsize=5);ax[1].axvline(0,color='black');ax[1].set_yticks([0],['DiD']);ax[1].set_title('ATT and 95% CI');plt.tight_layout();plt.show()"),
    ('事件研究、安慰剂与敏感性','以第 11 周为参照，用每周处理组交互项展示动态效应。上线前的伪时间点应无系统效果；改用不同对照城市检查稳定性。',"df['rel']=df.week-12\nfor w in weeks:\n if w!=11:df[f'e{w}']=((df.week==w)&(df.treated==1)).astype(int)\nterms=' + '.join(f'e{w}' for w in weeks if w!=11)\nes=smf.ols('wait ~ C(city)+C(week)+'+terms,data=df).fit(cov_type='cluster',cov_kwds={'groups':df.city})\ncoef=pd.DataFrame({'week':[w for w in weeks if w!=11],'estimate':[es.params[f'e{w}'] for w in weeks if w!=11],'se':[es.bse[f'e{w}'] for w in weeks if w!=11]})\nplt.figure(figsize=(10,4));plt.errorbar(coef.week,coef.estimate,yerr=1.96*coef.se,fmt='o',capsize=2);plt.axhline(0,color='black');plt.axvline(11.5,color='red',ls='--');plt.title('Event study relative to week 11');plt.show()\npre=df[df.week<12].copy();pre['fake']=(pre.week>=6)*pre.treated\nplacebo=smf.ols('wait ~ fake+C(city)+C(week)',data=pre).fit(cov_type='cluster',cov_kwds={'groups':pre.city})\nprint('Placebo:',placebo.params['fake'],placebo.pvalues['fake'])\nfor controls in ([4,5,6,7],[8,9,10,11]):\n d=df[(df.treated==1)|df.city.isin(controls)]\n m=smf.ols('wait ~ did+C(city)+C(week)',data=d).fit(cov_type='cluster',cov_kwds={'groups':d.city})\n print('Controls',controls,'ATT',round(m.params['did'],3))\nprint('Decision: simulated reduction only; actual causal claim requires credible city comparability and shock audit.')")
])

make('03_双边市场干扰.ipynb','Demo 3｜双边市场干扰与分流方案',
     '决策问题：司机激励如何影响共享供给下的订单？本 notebook 用简化的潜在结果模型说明干扰造成的偏差与设计权衡，不拟合真实派单机制。',[
    ('机制与目标量','模拟 12 区域、每区 100 笔订单。结果 = 基线 + 直接激励效应 0.6 + 区域平均激励暴露的溢出效应。目标是全量上线相对全量不上的效果 `direct + spillover`。',common+"\nfrom scipy.stats import norm\nG=12;m=100;direct=.6\ndef simulate(design,spill,rng):\n    if design=='order':z=rng.binomial(1,.5,(G,m))\n    elif design=='region':z=np.repeat(rng.binomial(1,.5,(G,1)),m,axis=1)\n    else:\n        z=np.repeat(rng.binomial(1,.5,(G,1)),m,axis=1)\n    exposure=z.mean(axis=1,keepdims=True)\n    if design=='switch':exposure=.75*exposure+.25*np.roll(exposure,1,axis=0)\n    y=8+direct*z+spill*exposure+rng.normal(0,1,(G,1))+rng.normal(0,.7,(G,m))\n    return y[z==1].mean()-y[z==0].mean() if z.min()!=z.max() else np.nan\nprint('Full rollout effect at spillover=0.8:',direct+.8)"),
    ('随机化比较与偏差','订单级分流让处理和对照共享供给，估计值更接近直接效应而非全量上线效果。区域级设计识别更多区域暴露效应，但区域数少时方差更大。时间切换以区域时间块示意，滞后供给会削弱隔离。',"records=[]\nfor spill in [0,.4,.8,1.2]:\n for design in ['order','region','switch']:\n  vals=np.array([simulate(design,spill,rng) for _ in range(250)])\n  for v in vals:records.append((spill,design,v,direct+spill))\nres=pd.DataFrame(records,columns=['spillover','design','estimate','target'])\nagg=res.groupby(['spillover','design']).estimate.agg(['mean','std']).reset_index();agg['bias']=agg['mean']-(direct+agg.spillover)\nprint(agg.round(3))\nfig,ax=plt.subplots(1,2,figsize=(12,4));sns.lineplot(data=agg,x='spillover',y='bias',hue='design',marker='o',ax=ax[0]);ax[0].axhline(0,color='black');ax[0].set_title('Bias against full rollout effect');sns.lineplot(data=agg,x='spillover',y='std',hue='design',marker='o',ax=ax[1]);ax[1].set_title('Monte Carlo standard deviation');plt.tight_layout();plt.show()"),
    ('估计分布与设计选择','查看溢出强度为 0.8 时的模拟分布。此处区域设计仍有区域间干扰和小簇数风险；真实方案需依据司机跨区流动、供需时段和预期效应选择隔离边界。',"s=res[res.spillover==.8]\nplt.figure(figsize=(9,4));sns.kdeplot(data=s,x='estimate',hue='design',fill=False,common_norm=False);plt.axvline(1.4,color='black',ls='--',label='full rollout');plt.legend();plt.title('Estimator distributions at spillover 0.8');plt.show()\nprint('Decision: choose region randomization if supply is mostly local; use longer switch blocks when temporal carryover can be measured; pilot the design before launch.')")
])

make('04_实验质量诊断助手.ipynb','Demo 4｜实验质量诊断与报告助手',
     '目标是把可自动化的质量诊断和报告草稿标准化。此处的“助手”是确定性规则与结构化文本生成，不调用外部大模型；每个结论可回溯到计算结果。',[
    ('实验登记、日志与指标字典','模拟登记、分流、曝光、结果表。故意让实验组曝光日志少 6%，用于演示异常识别。不能把未曝光样本从 ITT 主分析中删除。',common+"\nregistry={'experiment_id':'demo-exp-001','allocation':0.5,'unit':'user','primary':'orders','guardrail':'cancel','query_version':'sim-v1','owner':'demo'}\nmetric_dict={'orders':'7-day completed orders per assigned user','cancel':'7-day cancellation indicator'}\nn=4000;assigned=rng.binomial(1,.5,n);pre=rng.poisson(2,n)\nexposure=rng.binomial(1,np.where(assigned==1,.90,.96))\ndf=pd.DataFrame({'user_id':np.arange(n),'arm':assigned,'exposed':exposure,'pre_orders':pre,'orders':rng.poisson(1.4+.3*pre+.12*assigned),'cancel':rng.binomial(1,.12-.003*assigned,n)})\nprint(registry,metric_dict);print(df.head())"),
    ('自动诊断与阻断规则','SRM 阈值 p<0.001；组间曝光率差异超过 3 个百分点记为异常；基线差异用标准化均差 |SMD|>0.1。阈值是演示用规则，真实团队应按误报成本制定。',"count=df.arm.value_counts().sort_index();srm_p=stats.chisquare(count,[n/2,n/2]).pvalue\nex=df.groupby('arm').exposed.mean();base=df.groupby('arm').pre_orders.mean();pooled=np.sqrt(df.groupby('arm').pre_orders.var().mean());smd=(base[1]-base[0])/pooled\nchecks=pd.DataFrame([['SRM',srm_p,srm_p>=.001],['Exposure gap',abs(ex[1]-ex[0]),abs(ex[1]-ex[0])<=.03],['Baseline SMD',abs(smd),abs(smd)<=.1]],columns=['check','value','pass'])\nprint(checks)\nfig,ax=plt.subplots(1,2,figsize=(10,4));sns.barplot(data=df,x='arm',y='exposed',errorbar=None,ax=ax[0]);ax[0].set_title('Exposure rate');sns.barplot(data=checks,x='check',y='value',hue='pass',dodge=False,ax=ax[1]);ax[1].set_title('Diagnostic values');plt.tight_layout();plt.show()"),
    ('效果、样本路径与报告草稿','ITT 在所有已分配用户上计算。曝光差异可能反映日志缺失或真实触达差异，必须人工定位；诊断未通过时报告草稿标记“待复核”。',"def comparison(col):\n x=df.loc[df.arm==1,col];y=df.loc[df.arm==0,col];d=x.mean()-y.mean();se=np.sqrt(x.var(ddof=1)/len(x)+y.var(ddof=1)/len(y));return d,d-1.96*se,d+1.96*se\nmetrics=pd.DataFrame([('orders',*comparison('orders')),('cancel',*comparison('cancel'))],columns=['metric','effect','low','high']);print(metrics)\nflow=df.groupby('arm').agg(assigned=('user_id','size'),exposed=('exposed','sum'));print(flow)\nfig,ax=plt.subplots(1,2,figsize=(10,4));flow.plot(kind='bar',ax=ax[0]);ax[0].set_title('Assigned to exposed flow')\nfor i,row in metrics.iterrows():ax[1].errorbar(row.effect,i,xerr=[[row.effect-row.low],[row.high-row.effect]],fmt='o',capsize=5)\nax[1].axvline(0,color='black');ax[1].set_yticks(range(len(metrics)),metrics.metric);ax[1].set_title('ITT effects and 95% CI');plt.tight_layout();plt.show()\nstatus='待复核' if not checks['pass'].all() else '质量检查通过'\nreport=f'''实验 {registry['experiment_id']}｜查询版本 {registry['query_version']}\n数据来源：本 notebook 固定随机种子模拟；分析单元：{registry['unit']}。\n质量状态：{status}；异常项：{checks.loc[~checks['pass'],'check'].tolist()}。\n主指标 ITT：{metrics.loc[0,'effect']:.3f}，95% CI [{metrics.loc[0,'low']:.3f}, {metrics.loc[0,'high']:.3f}]。\n护栏效果：{metrics.loc[1,'effect']:.3f}。\n人工复核：曝光差异成因、分流与埋点一致性、干扰、实际成本和上线阈值。'''\nprint(report)")
])

make('05_非随机触达_匹配敏感性.ipynb','Demo 5｜非随机触达的匹配与敏感性分析',
     '目标是估计运营触达对留存的影响。处理并非随机，需先陈述“给定触达前协变量后无未测混杂”和重叠性假设。模拟数据刻意设置高活跃用户更易触达。',[
    ('模拟与选择偏差','`pre_activity`、`city`、`channel` 均在触达前；`treated` 运营触达；`retained` 七日留存。还模拟一个不可观测的兴趣变量，仅用于展示敏感性，不纳入主估计。',common+"\nfrom scipy.special import expit\nfrom sklearn.linear_model import LogisticRegression\nfrom sklearn.neighbors import NearestNeighbors\nn=7000;activity=rng.normal(size=n);city=rng.integers(0,4,n);channel=rng.binomial(1,.4,n);hidden=rng.normal(size=n)\nps_true=expit(-.3+.9*activity+.3*(city==0)+.25*channel+.25*hidden)\ntreated=rng.binomial(1,ps_true)\np_y=expit(-.4+.8*activity+.25*(city==0)+.2*channel+.3*hidden+.2*treated)\nretained=rng.binomial(1,p_y)\ndf=pd.DataFrame({'pre_activity':activity,'city':city,'channel':channel,'hidden_for_simulation':hidden,'treated':treated,'retained':retained})\nprint(df.head());print('Raw retention gap:',df.groupby('treated').retained.mean().diff().iloc[-1])"),
    ('倾向得分、重叠与协变量平衡','仅使用触达前可观测变量拟合倾向得分。先看两组得分分布；极端得分会使逆概率权重不稳定。以下估计的是重叠样本内的平均效果。',"X=pd.get_dummies(df[['pre_activity','city','channel']],columns=['city'],drop_first=True)\nmodel=LogisticRegression(max_iter=1000).fit(X,df.treated);df['ps']=np.clip(model.predict_proba(X)[:,1],.02,.98)\nkeep=df.ps.between(.05,.95);d=df[keep].copy();d['w']=np.where(d.treated==1,1/d.ps,1/(1-d.ps))\nfig,ax=plt.subplots(1,2,figsize=(11,4));sns.kdeplot(data=df,x='ps',hue='treated',ax=ax[0]);ax[0].set_title('Propensity overlap');sns.boxplot(data=d,x='treated',y='w',ax=ax[1]);ax[1].set_title('IPW weights');plt.tight_layout();plt.show()\ndef smd(v,t,w=None):\n w=np.ones(len(v)) if w is None else np.asarray(w);a=np.asarray(v);t=np.asarray(t);mu1=np.average(a[t==1],weights=w[t==1]);mu0=np.average(a[t==0],weights=w[t==0]);return (mu1-mu0)/np.sqrt((np.var(a[t==1])+np.var(a[t==0]))/2)\nbalance=pd.DataFrame({'feature':X.columns,'before':[smd(X.loc[keep,c],d.treated) for c in X],'after':[smd(X.loc[keep,c],d.treated,d.w) for c in X]});print(balance)\nb=balance.melt('feature',var_name='stage',value_name='smd');plt.figure(figsize=(8,4));sns.scatterplot(data=b,x='smd',y='feature',hue='stage');plt.axvline(-.1,color='gray',ls='--');plt.axvline(.1,color='gray',ls='--');plt.title('Covariate balance');plt.show()"),
    ('原始差异、加权与匹配','IPW 估计 ATE；1:1 最近邻匹配用处理组匹配对照组，目标更接近 ATT。这里的朴素区间仅用于教学，真实匹配推断应考虑匹配的不确定性。',"raw=df.groupby('treated').retained.mean().diff().iloc[-1]\nipw=np.average(d.loc[d.treated==1,'retained'],weights=d.loc[d.treated==1,'w'])-np.average(d.loc[d.treated==0,'retained'],weights=d.loc[d.treated==0,'w'])\nt=d[d.treated==1];c=d[d.treated==0];nn=NearestNeighbors(n_neighbors=1).fit(c[['ps']]);dist,idx=nn.kneighbors(t[['ps']]);pairs=t[dist[:,0]<.03].copy();matched=c.iloc[idx[dist[:,0]<.03,0]]\natt=pairs.retained.mean()-matched.retained.mean()\nest=pd.DataFrame({'method':['Raw','IPW ATE','Matched ATT'],'effect':[raw,ipw,att]});print(est)\nplt.figure(figsize=(7,4));sns.barplot(data=est,x='method',y='effect');plt.axhline(0,color='black');plt.title('Retention effect estimates');plt.show()"),
    ('未测混杂敏感性与决策','用透明的偏差参数做情景分析：若未观测因素造成 1、3、5 个百分点的虚假提升，调整后的效果会如何变化？这不是正式的识别保证，而是帮助业务方理解结论脆弱性。模拟中的隐藏变量仅用于事后校验。',"bias=np.array([0,.01,.03,.05,.08]);sensitivity=pd.DataFrame({'assumed_unmeasured_bias':bias,'adjusted_ipw_effect':ipw-bias});print(sensitivity)\nplt.figure(figsize=(7,4));sns.lineplot(data=sensitivity,x='assumed_unmeasured_bias',y='adjusted_ipw_effect',marker='o');plt.axhline(0,color='black');plt.title('Sensitivity to unmeasured bias');plt.show()\nprint('Simulation-only hidden variable difference:',df.groupby('treated').hidden_for_simulation.mean().diff().iloc[-1])\nprint('Decision: if modest unmeasured bias changes the sign, prioritize a randomized follow-up rather than claim causality.')")
])

analyses = {
    '01_补贴策略_AB实验.ipynb': """## 模拟结果解读与决策摘要

- 两组分别约 2891 与 3109 人，SRM 检验 p≈0.0049。若事先采用严格阈值 0.001，该项尚未触发阻断，但分流偏离仍值得排查；基线订单 p≈0.87，未见明显差异。
- 人均完单 ITT 约 **+0.273**，95% 区间约 **[+0.188,+0.359]**；CUPED 后约 **+0.272**，区间略窄，说明实验前行为提供了有限降方差收益。
- 模拟的每增量完单补贴成本约 **7.30 元**。是否推广仍取决于真实边际利润、留存价值和护栏表现；该成本比值未计其他运营成本。
- 分层效果是探索性信号；两个分层的置信区间重叠，不应仅据此宣称差异。司机共享供给可能使用户级随机实验低估或高估全量推广效果。
""",
    '02_城市灰度_DiD.ipynb': """## 模拟结果解读与决策摘要

- 处理城市的模拟接驾时长在上线前后下降，对照城市同期略上升。双重差分约 **-0.546 分钟**，常规城市聚类 95% 区间约 **[-0.621,-0.472]**。
- 前趋势差异斜率检验 p≈0.062，未达到常用 0.05 阈值，但这**不能证明**平行趋势成立；事件研究图和业务冲击排查仍重要。
- 伪上线时间的估计约 -0.029 分钟，p≈0.48。更换对照城市后点估计约 -0.599 与 -0.494 分钟，方向稳定但幅度变化。
- 只有 12 个城市簇，常规聚类标准误的推断可能过于乐观。真实项目应扩大城市样本或采用适合少簇情形的推断，并核查政策、天气及供需同期冲击。
""",
    '03_双边市场干扰.ipynb': """## 模拟结果解读与决策摘要

- 当溢出参数为 0.8 时，全量上线目标效应为 **1.4**。订单级分流的平均估计约 **0.615**，相对目标低约 **0.785**，因为两组共享区域供给。
- 区域级分流平均估计约 **1.464**，偏差较小，但 Monte Carlo 标准差约 **0.58**；订单级标准差仅约 **0.074**。降低污染会牺牲有效样本量。
- 示意性的时间切换设计平均估计约 **1.232**，仍受跨期残留影响。代码中的切换是简化暴露模型，不表示真实司机调度网络。
- 若司机跨区流动很强，区域级分流也无法充分隔离。真实设计需先画供需流动网络，再决定区域边界、切换周期及聚类推断方式。
""",
    '04_实验质量诊断助手.ipynb': """## 模拟结果解读与决策摘要

- SRM p≈0.635，基线 SMD≈0.002，均通过演示规则；实验组与对照组曝光率相差约 **5.5 个百分点**，超过预设 3 个百分点阈值，因此报告标记**待复核**。
- 全分配用户的完单 ITT 约 **+0.071**，95% 区间约 **[-0.022,+0.164]**；模拟样本尚不足以排除零效应或小幅负效应。取消率效果约 -0.006，区间也跨零。
- 下一步应先区分“真实曝光不足”和“曝光日志丢失”，核对实验组客户端/服务端日志链路。不能通过只保留曝光用户来修复 ITT。
- 结构化报告应保留实验 ID、查询版本、指标口径和审核人。自动生成的文字只复述计算证据，不能替代识别假设与上线决策审查。
""",
    '05_非随机触达_匹配敏感性.ipynb': """## 模拟结果解读与决策摘要

- 原始留存差约 **+18.6 个百分点**。处理组的实验前活跃度明显更高，原始 SMD≈0.80，简单组间比较严重混入选择偏差。
- 加权后各可观测协变量的 SMD 接近零；IPW 估计约 **+5.6 个百分点**，倾向得分匹配的 ATT 约 **+6.1 个百分点**。两个估计目标不同，不应要求数值完全一致。
- 若未观测因素带来约 5 个百分点的上偏，加权结果已接近零；8 个百分点上偏会使结论反向。模拟中确实存在未纳入主估计的兴趣变量。
- 因而这份观察性结果适合形成随机验证的优先级，不能直接认定触达带来了上述留存增量。真实研究还需检查权重极端值、共同支持和标准误。
""",
}
for filename, analysis in analyses.items():
    path = ROOT / filename
    nb = nbf.read(path, as_version=4)
    nb.cells.insert(-1, nbf.v4.new_markdown_cell(analysis))
    nbf.write(nb, path)

print('Generated five notebooks in', ROOT)
