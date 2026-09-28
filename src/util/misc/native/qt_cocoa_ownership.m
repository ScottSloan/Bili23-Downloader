// SPDX-License-Identifier: GPL-3.0-only
// Local runtime backport of Qt Gerrit 765434 / QTBUG-149612.
// The bundled Qt 6.9.3 owns real cells, but synthetic rows/cells borrow
// the table's accessibility ID. They must never delete that interface.
#import <AppKit/AppKit.h>
#import <objc/runtime.h>
#import <objc/message.h>
#include <stdint.h>
#include <string.h>
#include <dlfcn.h>

static IMP originalDealloc;
static IMP originalRemove;
static ptrdiff_t idOffset;
static ptrdiff_t roleOffset;
static Class elementClass;

static BOOL parentManaged(id object) {
    return *(id *)((char *)object + roleOffset) != nil;
}

static void guardedDealloc(id self, SEL cmd) {
    if (parentManaged(self)) {
        // QAccessibleCache::deleteInterface(0) is a no-op in Qt 6.9.3.
        // Keep all original Objective-C/child-array cleanup intact.
        *(uint32_t *)((char *)self + idOffset) = 0;
    }
    ((void (*)(id, SEL))originalDealloc)(self, cmd);
}

static void guardedRemove(id cls, SEL cmd, NSArray *array) {
    NSMutableArray *owned = [[NSMutableArray alloc] initWithCapacity:array.count];
    for (id cell in array) {
        if (!parentManaged(cell))
            [owned addObject:cell];
    }
    ((void (*)(id, SEL, NSArray *))originalRemove)(cls, cmd, owned);
    [owned release];
}

int bili23_install_qt_cocoa_ownership_fix(void) {
    if (originalDealloc)
        return 1;
    if (![NSThread isMainThread])
        return -1;
    elementClass = objc_getClass("QMacAccessibilityElement");
    if (!elementClass)
        return -2;
    Ivar axid = class_getInstanceVariable(elementClass, "axid");
    Ivar role = class_getInstanceVariable(elementClass, "synthesizedRole");
    Method dealloc = class_getInstanceMethod(elementClass, sel_registerName("dealloc"));
    Method remove = class_getClassMethod(elementClass, sel_registerName("removeElementsFromCache:"));
    if (!axid || !role || !dealloc || !remove)
        return -3;
    if (strcmp(ivar_getTypeEncoding(axid), "I") || ivar_getTypeEncoding(role)[0] != '@')
        return -4;
    idOffset = ivar_getOffset(axid);
    roleOffset = ivar_getOffset(role);
    originalRemove = method_setImplementation(remove, (IMP)guardedRemove);
    originalDealloc = method_setImplementation(dealloc, (IMP)guardedDealloc);
    return 0;
}
