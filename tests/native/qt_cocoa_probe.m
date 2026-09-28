#import <AppKit/AppKit.h>
#import <objc/runtime.h>
#import <objc/message.h>
#include <stdint.h>
#include <dlfcn.h>

// In-process regression probe, invoked only by the isolated test harness.
// Uses Qt's own objects; does not inspect or control any other application.
void bili23_test_activate(uintptr_t viewPointer) {
    ((void (*)(id, SEL))objc_msgSend)((id)viewPointer, sel_registerName("activateQtAccessibility"));
}

int bili23_test_selected_children(uint32_t tableId, int *badRoles) {
    Class cls = objc_getClass("QMacAccessibilityElement");
    id table = ((id (*)(id, SEL, uint32_t))objc_msgSend)(cls, sel_registerName("elementWithId:"), tableId);
    NSArray *children = ((id (*)(id, SEL))objc_msgSend)(table, sel_registerName("accessibilityChildren"));
    for (id child in children) {
        NSString *role = ((id (*)(id, SEL))objc_msgSend)(child, sel_registerName("accessibilityRole"));
        if ([role isEqual:NSAccessibilityRowRole])
            ((id (*)(id, SEL))objc_msgSend)(child, sel_registerName("accessibilityChildren"));
    }
    NSArray *selected = ((id (*)(id, SEL))objc_msgSend)(table, sel_registerName("accessibilitySelectedChildren"));
    int count = (int)selected.count;
    *badRoles = 0;
    NSString *tableRole = ((id (*)(id, SEL))objc_msgSend)(table, sel_registerName("accessibilityRole"));
    NSString *expectedRole = [tableRole isEqual:NSAccessibilityOutlineRole] ? NSAccessibilityGroupRole : NSAccessibilityCellRole;
    for (id cell in selected) {
        NSString *role = ((id (*)(id, SEL))objc_msgSend)(cell, sel_registerName("accessibilityRole"));
        if (![role isEqual:expectedRole]) {
            fprintf(stderr, "Unexpected selected role: %s\n", role.UTF8String);
            ++*badRoles;
        }
    }
    return count;
}

uintptr_t bili23_selected_children_offset(void) {
    Method m = class_getInstanceMethod(objc_getClass("QMacAccessibilityElement"), sel_registerName("accessibilitySelectedChildren"));
    IMP imp = method_getImplementation(m);
    Dl_info info;
    if (!dladdr((void *)imp, &info)) return 0;
    return (uintptr_t)imp - (uintptr_t)info.dli_fbase;
}
