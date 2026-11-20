-- Include the existing market's canonical website in worker-only context.
-- Required to reverify rolling applications after their first publication.
do $migration$
declare olddef text;updated text;
 old_token text:='m.state as market_state from public.vendor_opportunities o';
 new_token text:='m.state as market_state,m.website_url as market_website_url from public.vendor_opportunities o';
begin
 select pg_get_functiondef('public.btb_research_context()'::regprocedure) into olddef;
 if olddef is null or position(old_token in olddef)=0
 then raise exception 'Research context changed; do not patch blindly';end if;
 updated:=replace(olddef,old_token,new_token);
 execute updated;
end
$migration$;