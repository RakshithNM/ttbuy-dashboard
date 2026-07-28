from . import axis, bob, canara, hdfc, icici, idbi, iob, kotak, sbi

REGISTRY = {
    axis.PLUGIN.slug: axis.PLUGIN,
    iob.PLUGIN.slug: iob.PLUGIN,
    bob.PLUGIN.slug: bob.PLUGIN,
    canara.PLUGIN.slug: canara.PLUGIN,
    icici.PLUGIN.slug: icici.PLUGIN,
    sbi.PLUGIN.slug: sbi.PLUGIN,
    hdfc.PLUGIN.slug: hdfc.PLUGIN,
    kotak.PLUGIN.slug: kotak.PLUGIN,
    idbi.PLUGIN.slug: idbi.PLUGIN,
}
