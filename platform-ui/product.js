// Presentation-only projections. Source text never becomes a command or a verified fact.
const links=item=>item?.snapshot?.links || item?.links || {};
const label=value=>String(value || 'Unknown').replaceAll('_',' ').replace(/^./,letter=>letter.toUpperCase());
const completed=item=>item?.states?.lifecycle==='resolved';
const attention=item=>!completed(item) && (['in_review','awaiting_approval','ready'].includes(item?.states?.lifecycle) || ['proposed','blocked','approved'].includes(item?.states?.decision));

export function filterCases(cases,{query='',filter='all'}={}) {
  const needle=String(query).trim().toLocaleLowerCase('en');
  return cases.filter(item=>{
    const matches=!needle || [item.case_id,item.snapshot?.case_id,...Object.values(links(item))].some(value=>String(value || '').toLocaleLowerCase('en').includes(needle));
    return matches && (filter==='all' || filter==='open' && !completed(item) || filter==='attention' && attention(item) || filter==='completed' && completed(item));
  });
}

export function caseCounters(cases) {
  return {total:cases.length,open:cases.filter(item=>!completed(item)).length,attention:cases.filter(attention).length,completed:cases.filter(completed).length};
}

export function caseRequests(detail) {
  const decisions=detail.decisions || [],latest=decisions.at(-1);
  return [...decisions].reverse().map(decision=>{
    const current=decision===latest && decision.revision===detail.snapshot?.revision && decision.snapshot_hash===detail.snapshot?.snapshot_hash;
    const review=(detail.reviews || []).filter(item=>item.decision_id===decision.decision_id).at(-1);
    const receipt=(detail.actions || []).filter(item=>item.decision_id===decision.decision_id).at(-1);
    const status=!current?'Stale or superseded':receipt?'Sandbox receipt recorded':review?.verdict==='reject'?'Rejected by operator':review?.verdict==='approve'?'Approved by operator':'Awaiting human review';
    return {id:decision.decision_id,title:label(decision.action?.type),scope:'Internal proposal',status,current,revision:decision.revision,
      communication:'External communication not sent from this workspace.',outcome:'Physical delivery or return not confirmed.',
      receiptId:receipt?.action_id || receipt?.receipt_id || receipt?.id || null,
      slotStart:decision.action?.slot_start || null,slotEnd:decision.action?.slot_end || null};
  });
}

export function caseSummary(detail) {
  const events=detail.snapshot?.events || [],request=caseRequests(detail)[0];
  let title='Gather the original request',nextStep='Add source evidence to establish the customer request and its context.';
  if(events.length){title='Review the customer context';nextStep='Review the source evidence, then assess or propose the next step.';}
  if(request){
    title=request.title;
    if(!request.current)nextStep='Assess the current evidence and create a fresh proposal before review.';
    else if(request.status==='Sandbox receipt recorded')nextStep='Review the saved sandbox receipt. Physical delivery remains unconfirmed.';
    else if(request.status==='Rejected by operator')nextStep='Review the operator note and create a new proposal if follow-up is needed.';
    else if(request.status==='Approved by operator')nextStep='Review the approved proposal. Any sandbox execution requires a separate explicit action.';
    else nextStep='Review the current proposal, supporting evidence and customer consent before approval.';
  }
  const lastSource=[...events].reverse().find(event=>event.text && event.channel!=='internal') || [...events].reverse().find(event=>event.text);
  return {title,nextStep,owner:links(detail).operator_id || 'Not recorded',customer:links(detail).customer_id || 'Not recorded',order:links(detail).order_id || 'Not recorded',
    sourceExcerpt:lastSource?.text || '',sourceId:lastSource?.event_id || '',eventCount:events.length,requestCount:(detail.decisions || []).length,
    externalCommunication:'External communication not sent from this workspace.',physicalOutcome:'Physical delivery or return not confirmed.'};
}
