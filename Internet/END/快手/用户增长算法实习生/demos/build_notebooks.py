from pathlib import Path
import nbformat as nbf

D=Path(__file__).parent
def save(name, cells):
    nb=nbf.v4.new_notebook()
    nb.cells=[nbf.v4.new_markdown_cell(s) if k=='m' else nbf.v4.new_code_cell(s) for k,s in cells]
    nb.metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'}}
    nbf.write(nb,D/name)

setup="""import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from IPython.display import display
plt.style.use('seaborn-v0_8-whitegrid')
pd.options.display.float_format='{:.3f}'.format"""

save('01_uplift_and_budget.ipynb',[
('m',"""# 01 补贴增量效果与定向投放

**问题**：有限金币名额如何优先给真正因补贴而增加活跃的用户？本实验全部为合成数据。随机分组识别总体因果效应，潜在结果仅在模拟器中可见。"""),
('c',setup+"""
rng=np.random.default_rng(42); n=12000
X=pd.DataFrame({'activity':rng.normal(size=n),'sensitivity':rng.uniform(size=n),'tenure':rng.uniform(size=n)})
p0=1/(1+np.exp(-(-.4+.9*X.activity+.5*X.tenure)))
p1=np.clip(p0+np.clip(.04+.32*X.sensitivity-.08*X.activity,.01,.4),0,.99)
t=rng.binomial(1,.5,n); y=rng.binomial(1,np.where(t,p1,p0))
df=X.assign(treat=t,active=y,p0=p0,p1=p1,uplift=p1-p0)
display(df.head())
print('Randomized ATE:',df.loc[t==1,'active'].mean()-df.loc[t==0,'active'].mean(),'simulated truth:',df.uplift.mean())"""),
('m',"""## 随机化与异质性

处理前特征应基本平衡。自然活跃概率与补贴增量是不同的目标；不能把领取率或活跃预测分数当成增量。"""),
('c',"""fig,ax=plt.subplots(2,2,figsize=(11,8))
df.groupby('treat')[['activity','sensitivity','tenure']].mean().T.plot.bar(ax=ax[0,0],title='Feature balance')
df.groupby('treat').active.mean().plot.bar(ax=ax[0,1],title='Observed active rate',ylim=(0,1))
ax[1,0].hist(df.uplift,bins=30);ax[1,0].set(title='Heterogeneous uplift',xlabel='Incremental probability')
ax[1,1].scatter(df.p0.iloc[::20],df.uplift.iloc[::20],s=8,alpha=.3);ax[1,1].set(title='Natural activity vs uplift',xlabel='Baseline',ylabel='Uplift')
plt.tight_layout();plt.show()"""),
('m',"""## T-learner

分别拟合处理组和对照组活跃概率，并在留出的测试集上相减。真实业务还需时间切分、概率校准、泄漏排查。"""),
('c',"""tr,te=train_test_split(np.arange(n),test_size=.35,random_state=7,stratify=t)
models={}
for a in [0,1]:
    ix=tr[t[tr]==a]
    models[a]=LogisticRegression(max_iter=500).fit(X.iloc[ix],y[ix])
test=df.iloc[te].copy()
test['score']=models[1].predict_proba(X.iloc[te])[:,1]-models[0].predict_proba(X.iloc[te])[:,1]
test['natural']=models[0].predict_proba(X.iloc[te])[:,1]
print('Score-truth correlation:',test[['score','uplift']].corr().iloc[0,1])
display(test[['score','uplift','natural']].describe())"""),
('m',"""## 等预算策略比较

每个名额花费 1 单位。模拟器可计算潜在概率下的期望增量；现实不能直接观察个体真值，应以随机实验验证。"""),
('c',"""rows=[]
strategies={'uplift model':test.score.to_numpy(),'natural activity':test.natural.to_numpy(),'random':rng.random(len(test)),'oracle (simulation)':test.uplift.to_numpy()}
for name,score in strategies.items():
    order=np.argsort(-score)
    for frac in np.arange(.1,1.01,.1):
        chosen=order[:int(frac*len(test))]
        rows.append((name,frac,test.uplift.to_numpy()[chosen].sum(),test.uplift.to_numpy()[chosen].mean()))
result=pd.DataFrame(rows,columns=['strategy','budget_fraction','incremental_actives','incremental_per_subsidy'])
fig,ax=plt.subplots(1,2,figsize=(12,4))
for name,g in result.groupby('strategy'):
    ax[0].plot(g.budget_fraction,g.incremental_actives,label=name)
    ax[1].plot(g.budget_fraction,g.incremental_per_subsidy,label=name)
ax[0].set(title='Incremental actives',xlabel='Budget fraction')
ax[1].set(title='Efficiency',xlabel='Budget fraction',ylabel='Incremental actives per subsidy')
ax[0].legend(fontsize=8);plt.tight_layout();plt.show()
display(result[np.isclose(result.budget_fraction,.3)].sort_values('incremental_actives',ascending=False))"""),
('m',"""## 分桶校准与结论

预测分桶的实验估计存在随机噪声。上线需在同预算下随机比较增量 DAU、7/30 日留存、投诉和成本，并报告置信区间。真实数据至少包括随机组、处理前特征、曝光时间、实际成本及短长期结果。"""),
('c',"""test['decile']=pd.qcut(test.score,10,labels=False,duplicates='drop')
g=test.groupby('decile').agg(predicted=('score','mean'),truth=('uplift','mean'),size=('active','size'))
obs=test.groupby(['decile','treat']).active.mean().unstack()
g['experiment']=obs[1]-obs[0]
display(g)
g[['predicted','truth','experiment']].plot(marker='o',title='Uplift by predicted decile',ylabel='Incremental active probability')
plt.show()""")])

save('02_bid_and_offpolicy.ipynb',[
('m',"""# 02 多档补贴出价与离线评估

动作是 0、1、2、4 单位补贴。模拟历史策略偏向给敏感用户更高金额；日志保存动作概率。IPS 与 DR 需要正确的概率、重叠支持和一致的结果定义。"""),
('c',setup+"""
rng=np.random.default_rng(123);n=25000
X=pd.DataFrame({'sensitivity':rng.uniform(size=n),'baseline':rng.uniform(size=n)})
amounts=np.array([0,1,2,4]);p0=.12+.55*X.baseline.to_numpy()
potential=np.column_stack([np.clip(p0+(.22*X.sensitivity.to_numpy()+.04)*(1-np.exp(-a/1.5))-.012*a,.01,.98) for a in amounts])
x=X.sensitivity.to_numpy()
logits=np.column_stack([np.zeros(n),.3+x,.1+2*x,-.4+3*x])
prob=np.exp(logits-logits.max(axis=1,keepdims=True));prob/=prob.sum(axis=1,keepdims=True)
action=np.array([rng.choice(4,p=p) for p in prob])
reward=rng.binomial(1,potential[np.arange(n),action])
df=X.assign(action=action,amount=amounts[action],active=reward,propensity=prob[np.arange(n),action])
display(df.head());print('Minimum propensity:',df.propensity.min())"""),
('m',"""## 选择偏差

按金额观察的活跃率混合了金额效果和人群差异。“总体潜在均值”仅为模拟真值。"""),
('c',"""s=df.groupby('amount').agg(observed=('active','mean'),sensitivity=('sensitivity','mean'),count=('active','size'))
s['population_potential']=potential.mean(axis=0)
display(s)
fig,ax=plt.subplots(1,2,figsize=(11,4))
s[['observed','population_potential']].plot.bar(ax=ax[0],title='Observed vs potential')
s.sensitivity.plot.bar(ax=ax[1],title='Selection by sensitivity')
plt.tight_layout();plt.show()"""),
('m',"""## IPS、DR 与策略

在训练集拟合各动作结果模型，在独立测试日志上评估。候选策略的目标是活跃概率减金额成本；模拟最优策略仅用于校验。"""),
('c',"""tr,te=train_test_split(np.arange(n),test_size=.4,random_state=8)
models=[]
for a in range(4):
    ix=tr[action[tr]==a]
    models.append(LogisticRegression(max_iter=500).fit(X.iloc[ix],reward[ix]))
mu=np.column_stack([m.predict_proba(X.iloc[te])[:,1] for m in models])
pot=potential[te];ha=action[te];hp=prob[te,ha];r=reward[te]
cost=.025*amounts
policies={'no subsidy':np.zeros(len(te),dtype=int),'always 2':np.full(len(te),2),
          'model net value':np.argmax(mu-cost,axis=1),'oracle (simulation)':np.argmax(pot-cost,axis=1)}
def evaluate(target):
    w=(ha==target)/hp
    ips=np.mean(w*r)
    dr=np.mean(mu[np.arange(len(te)),target]+w*(r-mu[np.arange(len(te)),ha]))
    truth=np.mean(pot[np.arange(len(te)),target])
    return ips,dr,truth,np.mean(amounts[target]),w.sum()**2/(w@w)
table=pd.DataFrame({k:evaluate(v) for k,v in policies.items()},index=['IPS active','DR active','simulated truth','mean amount','IPS effective sample size']).T
display(table)"""),
('m',"""## 抽样波动和预算曲线

Bootstrap 展示单次离线评估的波动。通过搜索金额的影子价格近似满足人均预算；生产系统还需逐时 pacing。"""),
('c',"""target=policies['model net value'];w=(ha==target)/hp
base=mu[np.arange(len(te)),target];correction=w*(r-mu[np.arange(len(te)),ha])
boot=np.array([rng.integers(0,len(te),len(te)) for _ in range(200)])
fig,ax=plt.subplots(1,2,figsize=(11,4))
ax[0].hist(np.mean((w*r)[boot],axis=1),alpha=.6,label='IPS')
ax[0].hist(np.mean((base+correction)[boot],axis=1),alpha=.6,label='DR')
ax[0].axvline(np.mean(pot[np.arange(len(te)),target]),color='black',linestyle='--',label='truth')
ax[0].legend();ax[0].set(title='Bootstrap uncertainty',xlabel='Active rate')
rows=[]
for budget in np.linspace(0,.9,10):
    options=[]
    for price in np.linspace(0,.5,401):
        a=np.argmax(mu-price*amounts,axis=1);spend=np.mean(amounts[a])
        if spend<=budget+1e-9:options.append((np.mean(pot[np.arange(len(te)),a]),spend))
    value,spend=max(options);rows.append((budget,spend,value))
curve=pd.DataFrame(rows,columns=['budget','spend','expected_active'])
ax[1].plot(curve.budget,curve.expected_active,marker='o')
ax[1].set(title='Budget response',xlabel='Allowed mean amount',ylabel='Expected active rate')
plt.tight_layout();plt.show();display(curve)"""),
('m',"""## 结论与真实数据接口

历史策略与人群相关时，直接按金额比较会误导。IPS/DR 仍可能因 propensity 错误、缺乏重叠、延迟结果或未观测混杂而失效。真实日志至少需要候选动作集、动作选择概率、处理前特征、实际金额、结果和时间戳。生成式模型可产生候选金额，最终应经过预算、频控和体验约束筛选，再用随机实验验证。""")])

save('03_bandit_and_pacing.ipynb',[
('m',"""# 03 在线探索与预算节奏

三段变化的模拟环境，每轮一个用户，动作是 0/1/2 单位补贴。奖励为次日活跃价值减成本。比较固定、贪心、窗口 UCB；这些简化策略仅供教学。"""),
('c',"""import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display
plt.style.use('seaborn-v0_8-whitegrid')
rng=np.random.default_rng(2026);T=6000
amounts=np.array([0,1,2]);cost=.07*amounts
segments=np.repeat(np.arange(3),T//3)
prob=np.array([[.35,.48,.52],[.42,.51,.55],[.38,.44,.47]])[segments]
value=prob-cost;oracle=value.max(axis=1)
display(pd.DataFrame(np.array([[.35,.48,.52],[.42,.51,.55],[.38,.44,.47]])-cost,columns=amounts))"""),
('m',"""## 决策和预算护栏

窗口估计适应变化；UCB 给少观察的动作探索机会。每 200 轮设置预算块，选择前过滤不可支付动作。真实系统还需预测流量和长期反馈。"""),
('c',"""def run(kind,seed,budget=.9,block=200,window=350):
    rr=np.random.default_rng(seed);actions=[];net=[];active=[];spent=[]
    for t in range(T):
        if t%block==0:remaining=budget*block
        start=max(0,t-window)
        aa=np.array(actions[start:]);nn=np.array(net[start:])
        counts=np.array([(aa==a).sum() for a in range(3)])
        means=np.array([nn[aa==a].mean() if counts[a] else 0 for a in range(3)])
        if kind=='fixed':order=np.array([1,0,2])
        elif kind=='greedy':order=np.argsort(-means)
        else:
            score=means+np.sqrt(2*np.log(min(t,window)+2)/np.maximum(counts,1))
            score[counts==0]=np.inf
            order=np.argsort(-score)
        affordable=[a for a in order if amounts[a]<=remaining+1e-9]
        a=int(affordable[0]) if affordable else 0
        outcome=int(rr.random()<prob[t,a])
        actions.append(a);active.append(outcome);net.append(outcome-cost[a]);spent.append(amounts[a])
        remaining-=amounts[a]
    return pd.DataFrame({'action':actions,'active':active,'net':net,'spend':spent,
                         'expected_net':value[np.arange(T),actions],'oracle':oracle})
runs={k:run(k,2026+i) for i,k in enumerate(['fixed','greedy','ucb'])}
summary=pd.DataFrame({k:{'mean net':d.net.mean(),'mean expected net':d.expected_net.mean(),
                         'mean spend':d.spend.mean(),'total regret':(d.oracle-d.expected_net).sum()}
                      for k,d in runs.items()}).T
display(summary)"""),
('m',"""## 学习曲线

后悔值使用模拟器已知的潜在概率计算，现实业务中无法直接观察。虚线表示环境变化时点。"""),
('c',"""fig,ax=plt.subplots(2,2,figsize=(12,8))
for name,d in runs.items():
    ax[0,0].plot(d.net.expanding().mean(),label=name)
    ax[0,1].plot((d.oracle-d.expected_net).cumsum(),label=name)
    ax[1,0].plot(d.action.rolling(200,min_periods=1).mean(),label=name)
    ax[1,1].plot(d.spend.rolling(200,min_periods=1).mean(),label=name)
for a in ax.ravel():
    for boundary in [2000,4000]:a.axvline(boundary,color='gray',linestyle='--',alpha=.5)
ax[0,0].set(title='Cumulative mean realized net value')
ax[0,1].set(title='Cumulative expected regret')
ax[1,0].set(title='Rolling mean action',xlabel='Round')
ax[1,1].set(title='Rolling mean spend',xlabel='Round')
ax[0,0].legend();plt.tight_layout();plt.show()"""),
('m',"""## 预算敏感性

比较价值与花费，并验证任何 200 轮预算块都没有超支。注意块末可能被迫集中使用零补贴，实际需要更平滑的 pacing。"""),
('c',"""rows=[]
for budget in [.4,.7,1.,1.4]:
    for i,name in enumerate(['fixed','greedy','ucb']):
        d=run(name,100+int(budget*10)+i,budget=budget)
        rows.append((budget,name,d.expected_net.mean(),d.spend.mean(),d.groupby(np.arange(T)//200).spend.sum().max()))
s=pd.DataFrame(rows,columns=['budget','strategy','expected_net','mean_spend','max_block_spend'])
display(s)
fig,ax=plt.subplots(1,2,figsize=(11,4))
for name,g in s.groupby('strategy'):
    ax[0].plot(g.budget,g.expected_net,marker='o',label=name)
    ax[1].plot(g.budget,g.mean_spend,marker='o',label=name)
ax[0].set(title='Value vs budget',xlabel='Budget per round')
ax[1].set(title='Spend vs budget',xlabel='Budget per round')
ax[0].legend();plt.tight_layout();plt.show()
assert (s.max_block_spend<=s.budget*200+1e-8).all()"""),
('m',"""## 结论与真实数据接口

在线探索能适应变化，但会产生探索成本。这里没有用户特征、延迟反馈、干扰、欺诈或体验约束。上线应从安全基线和小流量实验开始，逐步加入上下文特征、频控、预算 pacing 和回退策略。真实日志需保存候选集、动作概率、预算状态、反馈时间及长期留存。""")])

