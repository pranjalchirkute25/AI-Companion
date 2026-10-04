(() => {
  'use strict';

  const $ = (selector) => document.querySelector(selector);
  const form = $('#decision-form');
  const results = $('#results');
  const state = { sessionId: null, input: null, analysis: null, question: '', answers: [], reflectionChoice: '' };
  const clean = (value) => String(value || '').trim();

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function fillList(container, items, render) {
    container.replaceChildren();
    (items || []).forEach((item) => container.append(render(item)));
  }
  function showError(id, message) {
    const node = $(id);
    node.textContent = message;
    node.hidden = false;
  }
  function hideError(id) { $(id).hidden = true; }
  async function post(url, payload) {
    const response = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || 'Something went wrong. Please try again.');
    return data;
  }

  function setFlow(step) {
    document.querySelectorAll('.flow-list li').forEach((item, index) => {
      item.classList.toggle('flow-active', index === step - 1);
      item.classList.toggle('flow-done', index < step - 1);
      item.querySelector('i').textContent = index < step - 1 ? '✓' : index === step - 1 ? '●' : '○';
    });
  }
  function drawRadar(analysis, input) {
    const explicitStakeholders = /family|team|colleague|customer|employee|partner|child|parent|community|client|cofounder/i.test(input.decision_description);
    const hasEvidence = /evidence|data|measured|confirmed|verified|offer|survey|trial|result|feedback/i.test(input.decision_description);
    const dimensions = [
      { name: 'Evidence', icon: '⌕', status: hasEvidence ? 'Partially explored' : 'Needs attention', why: hasEvidence ? 'You mention information to work from; it has not been independently verified here.' : 'No specific evidence or verification plan has surfaced yet.' },
      { name: 'Assumptions', icon: '◇', status: analysis.unstated_assumptions.length ? 'Partially explored' : 'Unexplored', why: analysis.unstated_assumptions.length ? `${analysis.unstated_assumptions.length} possible premise${analysis.unstated_assumptions.length === 1 ? '' : 's'} surfaced; you can decide whether they fit.` : 'The analysis did not identify a specific assumption to examine.' },
      { name: 'Alternatives', icon: '↗', status: input.options_considered || analysis.other_perspective ? 'Partially explored' : 'Needs attention', why: input.options_considered ? 'You named options and a counter-case; hybrid or reversible paths remain open to explore.' : 'A counter-case is offered, but your full option set is still unclear.' },
      { name: 'Stakeholders', icon: '◎', status: explicitStakeholders ? 'Partially explored' : 'Unexplored', why: explicitStakeholders ? 'Other people appear in the context; their needs and trade-offs may need a closer look.' : 'No affected people are explicit in the context yet. Consider who else may feel the effects.' },
      { name: 'Risks & consequences', icon: '⌁', status: analysis.overlooked_factors.length ? 'Needs attention' : 'Unexplored', why: analysis.overlooked_factors.length ? 'Possible gaps surfaced, but outcomes and second-order effects remain uncertain.' : 'Potential downsides and follow-on effects have not been mapped yet.' },
      { name: 'Reversibility', icon: '⤺', status: 'Unexplored', why: 'How easy this is to change later has not been established from the information provided.' },
    ];
    const host = $('#radar');
    fillList(host, dimensions, (dimension) => {
      const row = el('details', `radar-row state-${dimension.status.toLowerCase().replaceAll(' ', '-')}`);
      const summary = el('summary');
      summary.append(el('span', 'radar-icon', dimension.icon), el('span', 'radar-name', dimension.name), el('span', 'radar-state', dimension.status), el('span', 'radar-chevron', '⌄'));
      row.append(summary, el('p', 'radar-why', dimension.why));
      return row;
    });
  }
  function renderAnalysis(data, input) {
    state.analysis = data;
    state.sessionId = data.session_id;
    state.input = input;
    $('#session-label').textContent = '· SESSION ' + data.session_id.slice(0, 8).toUpperCase();
    const notice = $('#analysis-notice');
    notice.textContent = data.disclaimer || '';
    notice.hidden = !notice.textContent;
    notice.classList.toggle('notice-offline', notice.textContent.toLowerCase().includes('could not be generated'));
    $('#result-decision').textContent = input.decision_description.length > 120 ? input.decision_description.slice(0, 117) + '…' : input.decision_description;
    fillList($('#emphasized'), data.what_you_emphasized, (item) => el('span', 'tag', item));
    drawRadar(data, input);
    fillList($('#blindspots'), data.overlooked_factors, (item) => {
      const card = el('article', 'insight-card');
      card.append(el('span', 'mini-label', 'POTENTIAL BLIND SPOT'), el('h3', '', item.factor), el('p', '', item.why_it_matters), el('span', 'mini-label question-label', 'QUESTION TO EXAMINE'), el('p', 'card-question', item.factor.includes('?') ? item.factor : 'What would you want to know about ' + item.factor.toLowerCase() + '?'));
      return card;
    });
    fillList($('#assumptions'), data.unstated_assumptions, (item) => {
      const card = el('article', 'assumption-card');
      card.append(el('span', 'mini-label', 'POSSIBLE ASSUMPTION'), el('p', 'assumption-copy', item.assumption), el('p', 'why-copy', item.how_to_test));
      return card;
    });
    $('#perspective').textContent = data.other_perspective || 'A useful counter-case has not surfaced yet. What might someone who prefers another path point to?';
    state.question = (data.probing_questions || [])[0] || 'What information would most change how you see this decision?';
    showQuestion(state.question);
    renderBrief();
  }
  function showQuestion(question) {
    state.question = question;
    const box = $('#current-question');
    box.replaceChildren(el('span', 'mini-label', 'A QUESTION FROM YOUR MAP'), el('p', '', question));
    $('#answer').value = '';
  }
  function listSection(title, items) {
    const section = el('section', 'brief-section');
    section.append(el('h3', '', title));
    if (!items || !items.length) section.append(el('p', 'brief-muted', 'Not established yet — this is still open.'));
    else {
      const ul = el('ul');
      items.forEach((item) => ul.append(el('li', '', typeof item === 'string' ? item : `${item.assumption || item.factor || item.conflict_description}${item.why_it_matters ? ' — ' + item.why_it_matters : ''}`)));
      section.append(ul);
    }
    return section;
  }
  function renderBrief() {
    if (!state.analysis || !state.input) return;
    const { analysis, input } = state;
    const host = $('#brief-content');
    host.replaceChildren();
    const context = el('div', 'brief-section');
    context.append(el('h3', '', 'Decision & context'), el('p', '', input.decision_description), el('p', 'brief-muted', `What matters: ${input.drawing_factors}`));
    host.append(context);
    host.append(listSection('Options in view', (input.options_considered || '').split(/[,;\n]/).map(clean).filter(Boolean)));
    host.append(listSection('Possible assumptions', analysis.unstated_assumptions.map((x) => `${x.assumption} (to test: ${x.how_to_test})`)));
    host.append(listSection('Evidence & uncertainty', [input.deadline_or_stakes ? `Constraint or timing noted: ${input.deadline_or_stakes}` : '', 'Information in this brief comes from your description and AI-generated prompts; nothing has been externally verified.'].filter(Boolean)));
    host.append(listSection('Potential blind spots', analysis.overlooked_factors.map((x) => `${x.factor} — ${x.why_it_matters}`)));
    host.append(listSection('Stakeholders, risks & consequences', ['Who else may be affected has not been fully established.', 'Possible consequences are not predictions. Consider immediate, follow-on, and unintended effects.']));
    host.append(listSection('Pre-mortem', ['Imagine this decision went badly six months from now. What might have caused it? What early signal would you notice?']));
    const openQuestions = [...new Set([...(analysis.probing_questions || []).filter((question) => !state.answers.some((answer) => answer.question === question)), state.question].filter(Boolean))];
    host.append(listSection('Questions worth answering', openQuestions));
    host.append(listSection('What changed in your thinking', [state.answers.map((x) => x.answer).join(' · '), state.reflectionChoice, clean($('#reflection-note').value)].filter(Boolean)));
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const input = { decision_description: clean($('#decision-description').value), drawing_factors: clean($('#drawing-factors').value), options_considered: clean($('#options-considered').value) || null, deadline_or_stakes: clean($('#deadline-stakes').value) || null };
    if (input.decision_description.length < 10 || input.drawing_factors.length < 3) { showError('#form-error', 'Add a little more detail to both required fields.'); return; }
    hideError('#form-error');
    $('#loading').hidden = false; $('#analyze-button').disabled = true;
    try {
      const data = await post('/api/analyze', input);
      renderAnalysis(data, input); results.hidden = false; setFlow(2);
      results.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (error) { showError('#form-error', error.message); }
    finally { $('#loading').hidden = true; $('#analyze-button').disabled = false; }
  });

  $('#answer-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const answer = clean($('#answer').value);
    if (answer.length < 2 || !state.sessionId) return;
    hideError('#answer-error');
    const button = event.currentTarget.querySelector('button[type="submit"]');
    button.disabled = true; button.firstChild.textContent = 'Following your thought…';
    try {
      const data = await post('/api/followup', { session_id: state.sessionId, question: state.question, user_answer: answer });
      const next = [...(data.deeper_questions || []), ...(state.analysis.probing_questions || [])].find((question) => question !== state.question && !state.answers.some((answer) => answer.question === question)) || 'What would you want to verify before feeling ready to decide?';
      state.answers.push({ question: state.question, answer, summary: data.user_answer_summary, newlyExposed: data.newly_exposed_blind_spots || [], nextQuestion: next });
      const item = el('article', 'reflection-item');
      item.append(el('span', 'mini-label', `YOUR REFLECTION · ${state.answers.length}`), el('p', 'reflection-answer', answer), el('p', 'reflection-summary', data.user_answer_summary));
      if ((data.newly_exposed_blind_spots || []).length) item.append(el('p', 'reflection-summary', `New thread: ${data.newly_exposed_blind_spots.join(' · ')}`));
      $('#reflection').prepend(item);
      showQuestion(next); setFlow(3); renderBrief();
    } catch (error) { showError('#answer-error', error.message); }
    finally { button.disabled = false; button.firstChild.textContent = 'Explore this thought'; }
  });

  document.querySelectorAll('[data-reflection]').forEach((button) => button.addEventListener('click', () => {
    document.querySelectorAll('[data-reflection]').forEach((choice) => { choice.classList.toggle('selected', choice === button); choice.setAttribute('aria-pressed', choice === button ? 'true' : 'false'); });
    state.reflectionChoice = button.dataset.reflection; renderBrief();
  }));
  $('#reflection-note').addEventListener('input', renderBrief);
  $('#back-to-canvas').addEventListener('click', () => { $('#decision-description').focus(); window.scrollTo({ top: 0, behavior: 'smooth' }); });
  $('#new-decision').addEventListener('click', () => { form.reset(); results.hidden = true; state.sessionId = null; state.analysis = null; state.answers = []; state.reflectionChoice = ''; $('#reflection').replaceChildren(); setFlow(1); window.scrollTo({ top: 0, behavior: 'smooth' }); $('#decision-description').focus(); });
  $('#example-button').addEventListener('click', () => {
    $('#decision-description').value = 'I have an offer to join a small climate-tech company as an operations lead. The pay is 12% higher, but the company is early-stage and the role is broader than my current job. I have a young child and value predictable evenings. I do not yet know the team’s turnover or how often the role requires travel.';
    $('#drawing-factors').value = 'Meaningful work, growth, higher pay, and keeping evenings predictable.';
    $('#options-considered').value = 'Accept; stay in my current role; ask for a later start or clearer travel expectations.';
    $('#deadline-stakes').value = 'Offer response due in one week; cannot relocate.';
    $('#decision-description').focus();
  });
})();
