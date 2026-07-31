from . import axis, bob, canara, iob

REGISTRY = {
    axis.PLUGIN.slug: axis.PLUGIN,
    iob.PLUGIN.slug: iob.PLUGIN,
    bob.PLUGIN.slug: bob.PLUGIN,
    canara.PLUGIN.slug: canara.PLUGIN,
}
