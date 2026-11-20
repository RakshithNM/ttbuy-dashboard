from . import (
    axis,
    bandhan,
    bob,
    canara,
    citibank,
    cityunion,
    dbs,
    dcb,
    hdfc,
    hsbc,
    icici,
    idbi,
    idfcfirst,
    jkbank,
    kotak,
    kvb,
    iob,
    pnb,
    rbl,
    sbi,
    ujjivan,
    unionbank,
)

REGISTRY = {
    axis.PLUGIN.slug: axis.PLUGIN,
    iob.PLUGIN.slug: iob.PLUGIN,
    bob.PLUGIN.slug: bob.PLUGIN,
    canara.PLUGIN.slug: canara.PLUGIN,
    sbi.PLUGIN.slug: sbi.PLUGIN,
    hdfc.PLUGIN.slug: hdfc.PLUGIN,
    kotak.PLUGIN.slug: kotak.PLUGIN,
    idbi.PLUGIN.slug: idbi.PLUGIN,
    hsbc.PLUGIN.slug: hsbc.PLUGIN,
    jkbank.PLUGIN.slug: jkbank.PLUGIN,
    kvb.PLUGIN.slug: kvb.PLUGIN,
    ujjivan.PLUGIN.slug: ujjivan.PLUGIN,
    idfcfirst.PLUGIN.slug: idfcfirst.PLUGIN,
    dbs.PLUGIN.slug: dbs.PLUGIN,
    citibank.PLUGIN.slug: citibank.PLUGIN,
    icici.PLUGIN.slug: icici.PLUGIN,
    bandhan.PLUGIN.slug: bandhan.PLUGIN,
    dcb.PLUGIN.slug: dcb.PLUGIN,
    pnb.PLUGIN.slug: pnb.PLUGIN,
    rbl.PLUGIN.slug: rbl.PLUGIN,
    unionbank.PLUGIN.slug: unionbank.PLUGIN,
}

# Banks no longer scraped (their site blocks GitHub Actions runners). Their
# last fee entry in fees.json is carried over so the site keeps showing it
# next to their historical rates.
RETIRED = {
    cityunion.PLUGIN.slug: cityunion.PLUGIN,  # blocked since 2026-11-17
}
